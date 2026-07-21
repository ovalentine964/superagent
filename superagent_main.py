"""
SUPERAGENT Entry Point
Integrates the SUPERAGENT overlay with Hermes Agent's core capabilities.
"""
import asyncio
import logging
import os
import sys

# Add superagent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from superagent.agents.queen import QueenOrchestrator
from superagent.memory.store import UnifiedMemoryStore
from superagent.memory.learning import SelfImprovementEngine
from superagent.tools.registry import ToolRegistry
from superagent.gateway.router import MessageRouter
from superagent.gateway.telegram_handler import TelegramBot
from superagent.gateway.api_server import create_api_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("superagent")


async def main():
    """Boot the SUPERAGENT system."""
    logger.info("=" * 60)
    logger.info("SUPERAGENT v0.1.0 — Starting")
    logger.info("Merged OpenClaw + Hermes Agent")
    logger.info("=" * 60)

    # 1. Load config
    config_path = os.path.join(os.path.dirname(__file__), "superagent", "config.yaml")
    import yaml
    config = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

    # 2. Initialize memory
    db_path = config.get("memory", {}).get("db_path", "superagent.db")
    memory = UnifiedMemoryStore(db_path=db_path)
    await memory.initialize()
    logger.info("Memory system initialized")

    # 3. Initialize learning engine
    learning = SelfImprovementEngine(memory=memory)
    logger.info("Learning engine initialized")

    # 4. Initialize tool registry
    tool_registry = ToolRegistry()
    tool_registry.discover_tools()
    logger.info(f"Tools loaded: {len(tool_registry.tools)}")

    # 5. Initialize Queen orchestrator
    queen = QueenOrchestrator(config=config)
    queen.memory = memory
    queen.learning = learning
    logger.info("Queen orchestrator initialized")

    # 6. Initialize message router
    router = MessageRouter(queen=queen, memory=memory, config=config)

    # 7. Start Telegram bot
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if telegram_token:
        telegram_bot = TelegramBot(
            token=telegram_token,
            router=router,
            queen=queen,
        )
        logger.info("Telegram bot starting...")
        asyncio.create_task(telegram_bot.start())
    else:
        logger.warning("No TELEGRAM_BOT_TOKEN — Telegram disabled")

    # 8. Start API server
    api_host = os.environ.get("API_SERVER_HOST", "0.0.0.0")
    api_port = int(os.environ.get("PORT", os.environ.get("API_SERVER_PORT", "8642")))
    api_key = os.environ.get("API_SERVER_KEY", "")

    app = create_api_app(queen=queen, api_key=api_key)
    import uvicorn
    config_uvicorn = uvicorn.Config(
        app, host=api_host, port=api_port, log_level="info"
    )
    server = uvicorn.Server(config_uvicorn)
    logger.info(f"API server starting on {api_host}:{api_port}")

    # 9. Run both
    await asyncio.gather(
        server.serve(),
        telegram_bot.runner if telegram_token else asyncio.sleep(float("inf")),
    )


if __name__ == "__main__":
    asyncio.run(main())
