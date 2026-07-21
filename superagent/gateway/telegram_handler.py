"""
Telegram Bot Handler for SUPERAGENT.

Integrates with MessageRouter for unified message processing.
Inspired by OpenClaw's gateway + Hermes's channel system.
"""
from __future__ import annotations

import logging
from typing import Any

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from superagent.gateway.router import Channel, InboundMessage, MessageRouter

logger = logging.getLogger(__name__)


class TelegramHandler:
    """Telegram bot handler."""

    def __init__(
        self,
        token: str,
        router: MessageRouter,
        allowed_users: list[str] | None = None,
        webhook_url: str | None = None,
    ):
        self.token = token
        self.router = router
        self.allowed_users = [int(u) for u in (allowed_users or []) if u]
        self.webhook_url = webhook_url
        self._app: Application | None = None

    async def initialize(self) -> None:
        """Initialize the Telegram bot application."""
        self._app = (
            Application.builder()
            .token(self.token)
            .build()
        )

        # Register handlers
        self._app.add_handler(CommandHandler("start", self._handle_start))
        self._app.add_handler(CommandHandler("help", self._handle_help))
        self._app.add_handler(CommandHandler("status", self._handle_status))
        self._app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self._handle_text,
        ))

        # Set bot commands
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help"),
            BotCommand("status", "System status"),
        ]
        await self._app.initialize()
        await self._app.bot.set_my_commands(commands)
        logger.info("Telegram bot initialized")

    async def start_polling(self) -> None:
        """Start polling for updates."""
        if not self._app:
            await self.initialize()
        assert self._app is not None
        await self._app.start_polling(drop_pending_updates=True)
        logger.info("Telegram polling started")
        # Keep running
        await self._app.updater.start_polling(drop_pending_updates=True)

    async def stop(self) -> None:
        """Stop the bot."""
        if self._app:
            await self._app.stop()
            await self._app.shutdown()

    async def _is_allowed(self, update: Update) -> bool:
        """Check if user is allowed."""
        if not self.allowed_users:
            return True
        user_id = update.effective_user.id if update.effective_user else 0
        return user_id in self.allowed_users

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not await self._is_allowed(update):
            await update.message.reply_text("Access denied.")
            return
        await update.message.reply_text(
            "Welcome to SUPERAGENT!\n\n"
            "I'm your AI assistant powered by NVIDIA minimax m3.\n\n"
            "Send me any message and I'll route it to the right specialist."
        )

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if not await self._is_allowed(update):
            return
        await update.message.reply_text(
            "Commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help\n"
            "/status - System status\n\n"
            "Just send a message and I'll respond!"
        )

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        if not await self._is_allowed(update):
            return
        queen = getattr(context.application, '_queen', None)
        status = "running" if queen else "degraded"
        await update.message.reply_text(f"Status: {status}")

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages."""
        if not await self._is_allowed(update):
            await update.message.reply_text("Access denied.")
            return

        user_id = str(update.effective_user.id) if update.effective_user else "unknown"
        text = update.message.text

        # Show typing indicator
        await update.message.chat.send_action("typing")

        try:
            # Route through the Queen
            response = await self.router.handle_inbound(
                channel=Channel.TELEGRAM,
                user_id=user_id,
                content=text,
                message_id=str(update.message.message_id),
            )

            if response:
                await update.message.reply_text(response)
            else:
                await update.message.reply_text("I'm processing your request...")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text("Something went wrong. Please try again.")
