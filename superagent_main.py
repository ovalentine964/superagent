"""SUPERAGENT — Minimal entry point for Render."""
import os
import logging
from fastapi import FastAPI
import uvicorn

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
    
    # Try to initialize components
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from superagent.agents.queen import QueenOrchestrator
        queen = QueenOrchestrator()
        await queen.initialize()
        app.state.queen = queen
        logger.info("Queen orchestrator initialized")
    except Exception as e:
        logger.warning(f"Queen init failed: {e}")
        app.state.queen = None

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

    # Telegram
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
            import asyncio
            asyncio.create_task(tg.start_polling())
            logger.info("Telegram bot started")
        except Exception as e:
            logger.warning(f"Telegram init failed: {e}")

    logger.info("SUPERAGENT ready!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8642"))
    uvicorn.run(app, host="0.0.0.0", port=port)
