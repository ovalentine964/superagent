"""SUPERAGENT — Merged OpenClaw + Hermes Agent."""
import os
import sys
import logging
import asyncio
from fastapi import FastAPI
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("superagent")

app = FastAPI(title="SUPERAGENT", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "superagent", "version": "0.1.0"}


@app.get("/")
async def root():
    return {"status": "running", "service": "superagent"}


@app.on_event("startup")
async def startup():
    logger.info("SUPERAGENT v0.1.0 starting...")

    # Set NVIDIA API key from env
    nvidia_key = os.environ.get("NVIDIA_API_KEY", "")
    if nvidia_key:
        os.environ["NVIDIA_API_KEY"] = nvidia_key
        logger.info("NVIDIA API key configured")

    # Load config
    import yaml
    config_path = os.path.join(os.path.dirname(__file__), "superagent", "config.yaml")
    config = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

    # Initialize Queen
    try:
        from superagent.agents.queen import QueenOrchestrator
        model = config.get("llm", {}).get("default_model", "nvidia/minimaxai/minimax-m3")
        queen = QueenOrchestrator(model=model)
        await queen.initialize()
        app.state.queen = queen
        logger.info(f"Queen initialized with model: {model}")
    except Exception as e:
        logger.warning(f"Queen init failed: {e}")
        app.state.queen = None

    # Initialize Router
    try:
        from superagent.gateway.router import MessageRouter
        router = MessageRouter()
        if app.state.queen:
            router.set_queen(app.state.queen)
        app.state.router = router
        logger.info("Router initialized")
    except Exception as e:
        logger.warning(f"Router init failed: {e}")
        app.state.router = None

    # Start Telegram
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
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
            asyncio.create_task(tg.start_polling())
            logger.info("Telegram bot started")
        except Exception as e:
            logger.warning(f"Telegram init failed: {e}")

    logger.info("SUPERAGENT ready!")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8642"))
    uvicorn.run(app, host="0.0.0.0", port=port)
