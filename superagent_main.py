"""SUPERAGENT — Merged OpenClaw + Hermes Agent."""
import os
import sys
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("superagent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global tg_app
    logger.info("SUPERAGENT v0.1.0 starting...")

    import yaml
    config_path = os.path.join(os.path.dirname(__file__), "superagent", "config.yaml")
    config = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

    # Queen
    try:
        from superagent.agents.queen import QueenOrchestrator
        model = config.get("llm", {}).get("default_model", "nvidia/minimaxai/minimax-m3")
        queen = QueenOrchestrator(model=model)
        await queen.initialize()
        app.state.queen = queen
        logger.info(f"Queen ready (model: {model})")
    except Exception as e:
        logger.error(f"Queen failed: {e}")
        app.state.queen = None

    # Router
    try:
        from superagent.gateway.router import MessageRouter
        router = MessageRouter()
        if app.state.queen:
            router.set_queen(app.state.queen)
        app.state.router = router
        logger.info("Router ready")
    except Exception as e:
        logger.error(f"Router failed: {e}")
        app.state.router = None

    # Telegram
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    tg_app = None
    if tg_token and app.state.router:
        try:
            from superagent.gateway.telegram_handler import TelegramHandler
            allowed = os.environ.get("TELEGRAM_CHAT_ID", "").split(",")
            tg = TelegramHandler(
                token=tg_token,
                router=app.state.router,
                allowed_users=[u for u in allowed if u] or None,
            )
            await tg.initialize()
            tg_app = tg
            asyncio.create_task(_run_telegram(tg))
            logger.info("Telegram polling started")
        except Exception as e:
            logger.error(f"Telegram failed: {e}")

    logger.info("SUPERAGENT ready!")
    yield
    if tg_app:
        await tg_app.stop()
    logger.info("SUPERAGENT stopped")


async def _run_telegram(tg):
    """Run Telegram polling with error handling."""
    try:
        await tg.start_polling()
    except Exception as e:
        logger.error(f"Telegram polling error: {e}")


app = FastAPI(title="SUPERAGENT", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "superagent", "version": "0.1.0"}


@app.get("/")
async def root():
    return {"status": "running", "service": "superagent"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8642"))
    uvicorn.run(app, host="0.0.0.0", port=port)
