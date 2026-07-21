"""SUPERAGENT Entry Point — Merged OpenClaw + Hermes Agent."""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    import yaml
    config_path = os.path.join(os.path.dirname(__file__), "superagent", "config.yaml")
    config = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

    # 2. Initialize memory
    from superagent.memory.store import UnifiedMemoryStore
    db_path = config.get("memory", {}).get("db_path", "superagent.db")
    memory = UnifiedMemoryStore(db_path=db_path)
    await memory.initialize()
    logger.info("Memory system initialized")

    # 3. Initialize learning engine
    from superagent.memory.learning import LearningEngine
    learning = LearningEngine(memory=memory)
    logger.info("Learning engine initialized")

    # 4. Initialize tool registry
    from superagent.tools.registry import ToolRegistry
    tool_registry = ToolRegistry()
    tool_registry.discover_tools()
    logger.info(f"Tools loaded: {len(tool_registry.tools)}")

    # 5. Initialize Queen orchestrator
    from superagent.agents.queen import QueenOrchestrator
    queen = QueenOrchestrator(config=config)
    queen.memory = memory
    queen.learning = learning
    logger.info("Queen orchestrator initialized")

    # 6. Initialize message router
    from superagent.gateway.router import MessageRouter
    router = MessageRouter(queen=queen, memory=memory, config=config)

    # 7. Start Telegram bot
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if telegram_token:
        from superagent.gateway.telegram_handler import TelegramBot
        telegram_bot = TelegramBot(
            token=telegram_token,
            router=router,
            queen=queen,
        )
        logger.info("Telegram bot starting...")
        asyncio.create_task(telegram_bot.start())
    else:
        logger.warning("No TELEGRAM_BOT_TOKEN — Telegram disabled")
        telegram_bot = None

    # 8. Start API server
    from superagent.gateway.api_server import create_api_app
    import uvicorn

    api_host = os.environ.get("API_SERVER_HOST", "0.0.0.0")
    api_port = int(os.environ.get("PORT", os.environ.get("API_SERVER_PORT", "8642")))
    api_key = os.environ.get("API_SERVER_KEY", "")

    app = create_api_app(queen=queen, api_key=api_key)
    config_uvicorn = uvicorn.Config(app, host=api_host, port=api_port, log_level="info")
    server = uvicorn.Server(config_uvicorn)
    logger.info(f"API server starting on {api_host}:{api_port}")

    # 9. Run
    tasks = [server.serve()]
    if telegram_bot:
        tasks.append(telegram_bot.runner())
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
