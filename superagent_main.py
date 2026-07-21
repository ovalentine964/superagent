"""SUPERAGENT — Merged OpenClaw + Hermes Agent."""
import os
import sys
import logging
import asyncio
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("superagent")


def run_telegram_bot(token, router, allowed_users):
    """Run Telegram bot in a separate thread with its own event loop."""
    import asyncio as _asyncio
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

    loop = _asyncio.new_event_loop()
    _asyncio.set_event_loop(loop)

    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return
        user_id = str(update.effective_user.id)
        text = update.message.text
        chat_id = str(update.message.chat_id)

        logger.info(f"Telegram received: {text[:50]} from {user_id}")
        await update.message.chat.send_action("typing")

        try:
            from superagent.gateway.router import Channel, InboundMessage
            import time
            inbound = InboundMessage(
                channel=Channel.TELEGRAM,
                channel_message_id=str(update.message.message_id),
                user_id=user_id,
                chat_id=chat_id,
                content=text,
                timestamp=time.time(),
            )
            response = await router.handle_message(inbound)
            if response and response.content:
                await update.message.reply_text(response.content)
            else:
                await update.message.reply_text("Processing...")
        except Exception as e:
            logger.error(f"Handler error: {e}", exc_info=True)
            await update.message.reply_text(f"Error: {str(e)[:200]}")

    async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Welcome to SUPERAGENT! Send me a message.")

    async def post_init(app):
        logger.info("Telegram bot post_init - polling starting")

    try:
        app = Application.builder().token(token).post_init(post_init).build()
        app.add_handler(CommandHandler("start", handle_start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        logger.info("Starting Telegram polling...")
        loop.run_until_complete(app.run_polling(drop_pending_updates=True))
    except Exception as e:
        logger.error(f"Telegram polling error: {e}", exc_info=True)
    finally:
        loop.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SUPERAGENT v0.1.0 starting...")

    import yaml
    config_path = os.path.join(os.path.dirname(__file__), "superagent", "config.yaml")
    config = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

    # Initialize Queen
    queen = None
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

    # Initialize Router
    router = None
    try:
        from superagent.gateway.router import MessageRouter
        router = MessageRouter()
        if queen:
            router.set_queen(queen)
        app.state.router = router
        logger.info("Router ready")
    except Exception as e:
        logger.error(f"Router failed: {e}")
        app.state.router = None

    # Start Telegram in background thread
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if tg_token and router:
        allowed = os.environ.get("TELEGRAM_CHAT_ID", "").split(",")
        allowed_users = [u for u in allowed if u]
        tg_thread = threading.Thread(
            target=run_telegram_bot,
            args=(tg_token, router, allowed_users),
            daemon=True
        )
        tg_thread.start()
        logger.info("Telegram thread started")

    logger.info("SUPERAGENT ready!")
    yield
    logger.info("SUPERAGENT stopped")


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
