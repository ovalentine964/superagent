"""SUPERAGENT Entry Point."""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("superagent")


async def main():
    logger.info("SUPERAGENT v0.1.0 starting...")

    # Queen
    from superagent.agents.queen import QueenOrchestrator
    queen = QueenOrchestrator()
    await queen.initialize()
    logger.info("Queen ready")

    # Router
    from superagent.gateway.router import MessageRouter
    router = MessageRouter()
    router.set_queen(queen)
    logger.info("Router ready")

    # Telegram
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    tg_handler = None
    if tg_token:
        from superagent.gateway.telegram_handler import TelegramHandler
        allowed = os.environ.get("TELEGRAM_CHAT_ID", "").split(",")
        tg_handler = TelegramHandler(
            token=tg_token,
            router=router,
            allowed_users=[u for u in allowed if u] or None,
        )
        await tg_handler.initialize()
        logger.info("Telegram ready")

    # API Server
    from superagent.gateway.api_server import create_app
    import uvicorn

    api_key = os.environ.get("API_SERVER_KEY", "")
    port = int(os.environ.get("PORT", "8642"))

    app = create_app(router=router, auth_token=api_key or None)
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info"))
    logger.info(f"API on port {port}")

    # Run
    tasks = [server.serve()]
    if tg_handler:
        tasks.append(tg_handler.start_polling())
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
