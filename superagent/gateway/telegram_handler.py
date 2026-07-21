"""Telegram Bot Handler for SUPERAGENT."""
from __future__ import annotations

import logging
import time
from typing import Any

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from superagent.gateway.router import Channel, InboundMessage, OutboundMessage, MessageRouter

logger = logging.getLogger(__name__)


class TelegramHandler:
    """Telegram bot handler."""

    def __init__(
        self,
        token: str,
        router: MessageRouter,
        allowed_users: list[str] | None = None,
    ):
        self.token = token
        self.router = router
        self.allowed_users = [int(u) for u in (allowed_users or []) if u]
        self._app: Application | None = None

    async def initialize(self) -> None:
        """Initialize the Telegram bot."""
        self._app = (
            Application.builder()
            .token(self.token)
            .build()
        )
        self._app.add_handler(CommandHandler("start", self._handle_start))
        self._app.add_handler(CommandHandler("help", self._handle_help))
        self._app.add_handler(CommandHandler("status", self._handle_status))
        self._app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self._handle_text,
        ))
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help"),
            BotCommand("status", "System status"),
        ]
        await self._app.initialize()
        await self._app.bot.set_my_commands(commands)
        logger.info("Telegram bot initialized")

    async def run_polling(self) -> None:
        """Run polling (blocks until stopped)."""
        if not self._app:
            await self.initialize()
        assert self._app is not None
        await self._app.run_polling(drop_pending_updates=True)

    async def stop(self) -> None:
        """Stop the bot."""
        if self._app:
            await self._app.stop()
            await self._app.shutdown()

    def _is_allowed(self, user_id: int) -> bool:
        if not self.allowed_users:
            return True
        return user_id in self.allowed_users

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update.effective_user.id):
            await update.message.reply_text("Access denied.")
            return
        await update.message.reply_text(
            "Welcome to SUPERAGENT!\n\n"
            "I'm your AI assistant powered by NVIDIA minimax m3.\n"
            "Send me any message!"
        )

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update.effective_user.id):
            return
        await update.message.reply_text(
            "Commands:\n/start - Start\n/help - Help\n/status - Status\n\n"
            "Just send a message and I'll respond!"
        )

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_allowed(update.effective_user.id):
            return
        queen = getattr(self.router, '_queen', None)
        status = "running" if queen else "degraded"
        await update.message.reply_text(f"Status: {status}")

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages by routing through Queen."""
        if not update.message or not update.message.text:
            return
        if not self._is_allowed(update.effective_user.id):
            await update.message.reply_text("Access denied.")
            return

        user_id = str(update.effective_user.id)
        chat_id = str(update.message.chat_id)
        text = update.message.text

        logger.info(f"Received from {user_id}: {text[:50]}")

        # Show typing
        await update.message.chat.send_action("typing")

        try:
            # Create inbound message
            inbound = InboundMessage(
                channel=Channel.TELEGRAM,
                channel_message_id=str(update.message.message_id),
                user_id=user_id,
                chat_id=chat_id,
                content=text,
                timestamp=time.time(),
            )

            # Route through Queen
            response = await self.router.handle_message(inbound)

            if response and response.content:
                await update.message.reply_text(response.content)
            else:
                await update.message.reply_text("I'm thinking... try again in a moment.")
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await update.message.reply_text(f"Error: {str(e)[:100]}")
