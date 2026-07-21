"""
SUPERAGENT — Main Entry Point

Starts the full system:
1. Load configuration
2. Initialize database
3. Initialize tool registry
4. Initialize memory system
5. Initialize learning engine
6. Initialize Queen orchestrator
7. Start Telegram bot
8. Start API server
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path

import structlog
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = structlog.get_logger()


async def main() -> None:
    """Main entry point for SUPERAGENT."""
    import yaml

    # Load configuration
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    logger.info("superagent_starting", version="0.1.0")

    # ── 1. Initialize Database ──────────────────────────────────
    from data.migrations import init_db

    db_url = os.getenv("DATABASE_URL", "sqlite:///./data/superagent.db")
    engine = init_db(db_url)
    logger.info("database_ready")

    # ── 2. Initialize Tool Registry ─────────────────────────────
    from tools.registry import ToolRegistry

    registry = ToolRegistry.get_instance()

    # Register built-in tools
    from tools.communication_tools import register as register_comm
    from tools.market_tools import register as register_market

    register_market(registry)
    register_comm(registry)

    # Discover additional tools
    tool_dirs = config.get("tools", {}).get("registry", {}).get("tool_dirs", ["./tools"])
    discovered = await registry.discover_modules(tool_dirs)
    logger.info("tools_registered", total=len(registry.list_tools()), discovered=discovered)

    # ── 3. Initialize Memory System ─────────────────────────────
    import redis as redis_lib

    from memory.knowledge import KnowledgeBase
    from memory.learning import LearningEngine
    from memory.store import UnifiedMemoryStore

    # Redis connection
    redis_client = None
    try:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD")
        redis_client = redis_lib.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            decode_responses=True,
        )
        redis_client.ping()
        logger.info("redis_connected", host=redis_host, port=redis_port)
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e))

    # Unified memory store
    workspace_path = config.get("system", {}).get("workspace_dir", "./workspace")
    memory_store = UnifiedMemoryStore(
        workspace_path=workspace_path,
        db_path="./data/sessions.db",
        redis_client=redis_client,
        write_approval=config.get("security", {}).get("memory_write_approval", False),
    )
    logger.info("memory_store_ready")

    # Knowledge base (ChromaDB)
    knowledge_base = None
    try:
        chroma_host = os.getenv("CHROMADB_HOST", "localhost")
        chroma_port = int(os.getenv("CHROMADB_PORT", "8000"))
        knowledge_base = KnowledgeBase(
            chroma_host=chroma_host,
            chroma_port=chroma_port,
        )
        await knowledge_base.initialize()
        logger.info("knowledge_base_ready")
    except Exception as e:
        logger.warning("knowledge_base_unavailable", error=str(e))

    # Learning engine
    learning_engine = LearningEngine(
        skills_path=os.path.join(workspace_path, "skills"),
        memory_path=os.path.join(workspace_path, "memory"),
        write_approval=config.get("security", {}).get("memory_write_approval", False),
    )
    learning_engine.load_skills()
    logger.info("learning_engine_ready", skills=len(learning_engine._skill_cache))

    # ── 4. Initialize Agents ────────────────────────────────────
    from agents.queen import QueenOrchestrator

    default_model = config.get("llm", {}).get("default_model", "anthropic/claude-sonnet-4-20250514")
    queen = QueenOrchestrator(
        model=default_model,
        workspace_path=workspace_path,
    )
    await queen.initialize()
    logger.info("queen_ready")

    # ── 5. Initialize Gateway ───────────────────────────────────
    from gateway.router import MessageRouter

    # Parse allowed users
    allowed_users = {}
    telegram_users = os.getenv("TELEGRAM_ALLOWED_USERS", "")
    if telegram_users:
        allowed_users["telegram"] = [u.strip() for u in telegram_users.split(",") if u.strip()]

    router = MessageRouter(allowed_users=allowed_users)
    router.set_queen(queen)

    # ── 6. Start Telegram Bot ───────────────────────────────────
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_handler = None

    if telegram_token:
        from gateway.telegram_handler import TelegramHandler

        telegram_handler = TelegramHandler(
            token=telegram_token,
            router=router,
        )
        await telegram_handler.initialize()

        webhook_url = config.get("gateway", {}).get("channels", {}).get("telegram", {}).get("webhook_url")
        if webhook_url:
            await telegram_handler.start_webhook(webhook_url)
        else:
            await telegram_handler.start_polling()

        logger.info("telegram_started")
    else:
        logger.info("telegram_disabled", reason="no token")

    # ── 7. Start API Server ─────────────────────────────────────
    from gateway.api_server import create_app

    api_token = os.getenv("API_AUTH_TOKEN")
    cors_origins = config.get("gateway", {}).get("channels", {}).get("api", {}).get("cors_origins", ["*"])

    app = create_app(
        router=router,
        auth_token=api_token,
        cors_origins=cors_origins,
    )

    api_host = config.get("gateway", {}).get("host", "0.0.0.0")
    api_port = config.get("gateway", {}).get("port", 8080)

    logger.info("api_server_starting", host=api_host, port=api_port)

    # ── 8. Run ──────────────────────────────────────────────────
    # Graceful shutdown handler
    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("shutdown_signal_received")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    # Start uvicorn in the background
    uvicorn_config = uvicorn.Config(
        app=app,
        host=api_host,
        port=api_port,
        log_level="info",
    )
    server = uvicorn.Server(uvicorn_config)

    # Run both the API server and wait for shutdown
    server_task = asyncio.create_task(server.serve())

    logger.info(
        "superagent_ready",
        api=f"http://{api_host}:{api_port}",
        telegram="enabled" if telegram_handler else "disabled",
        tools=len(registry.list_tools()),
    )

    # Wait for shutdown signal
    await shutdown_event.wait()

    # Cleanup
    logger.info("shutting_down")
    server.should_exit = True
    await server_task

    if telegram_handler:
        await telegram_handler.stop()

    if redis_client:
        redis_client.close()

    logger.info("superagent_stopped")


if __name__ == "__main__":
    asyncio.run(main())
