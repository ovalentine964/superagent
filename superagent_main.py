"""SUPERAGENT — Minimal working version."""
import os
import sys
import logging
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("superagent")


def run_telegram(token):
    """Run a simple echo bot."""
    import asyncio
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        text = update.message.text or ""
        logger.info(f"Got message: {text[:50]}")
        try:
            await update.message.reply_text(f"Echo: {text}")
        except Exception as e:
            logger.error(f"Reply error: {e}")

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("SUPERAGENT online!")

    async def post_init(app):
        logger.info("Bot ready")

    try:
        app = Application.builder().token(token).post_init(post_init).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        logger.info("Starting polling...")
        loop.run_until_complete(app.run_polling(drop_pending_updates=True))
    except Exception as e:
        logger.error(f"Polling error: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SUPERAGENT starting...")

    # Start Telegram
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if tg_token:
        t = threading.Thread(target=run_telegram, args=(tg_token,), daemon=True)
        t.start()
        logger.info("Telegram thread started")

    logger.info("SUPERAGENT ready!")
    yield
    logger.info("SUPERAGENT stopped")


app = FastAPI(title="SUPERAGENT", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "superagent"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8642"))
    uvicorn.run(app, host="0.0.0.0", port=port)
