"""
Telegram Bot Handler

Full-featured Telegram integration using python-telegram-bot v22+.

Features:
- Command handling (/start, /help, /status, /task, /report)
- Message routing through the MessageRouter
- Media support (images, documents, voice)
- Inline keyboard support
- Webhook and polling modes
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from gateway.router import Channel, InboundMessage, MessageRouter, OutboundMessage

logger = structlog.get_logger()


class TelegramHandler:
    """
    Telegram bot handler for SUPERAGENT.

    Integrates with the MessageRouter for unified message processing.
    """

    def __init__(
        self,
        token: str,
        router: MessageRouter,
        allowed_users: list[str] | None = None,
        webhook_url: str | None = None,
    ):
        self.token = token
        self.router = router
        self.allowed_users = allowed_users or []
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
        self._app.add_handler(CommandHandler("task", self._handle_task))
        self._app.add_handler(CommandHandler("report", self._handle_report))
        self._app.add_handler(CommandHandler("skills", self._handle_skills))
        self._app.add_handler(CallbackQueryHandler(self._handle_callback))
        self._app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self._handle_text,
        ))
        self._app.add_handler(MessageHandler(
            filters.PHOTO | filters.Document.ALL | filters.VOICE,
            self._handle_media,
        ))

        # Register the delivery handler with the router
        self.router.register_channel(Channel.TELEGRAM, self._deliver_message)

        # Set bot commands
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help"),
            BotCommand("status", "System status"),
            BotCommand("task", "Create a task"),
            BotCommand("report", "Generate a report"),
            BotCommand("skills", "List available skills"),
        ]

        await self._app.initialize()
        await self._app.bot.set_my_commands(commands)

        logger.info("telegram_handler_initialized")

    async def start_polling(self) -> None:
        """Start the bot in polling mode."""
        if not self._app:
            await self.initialize()
        assert self._app is not None
        await self._app.start_polling(drop_pending_updates=True)
        logger.info("telegram_polling_started")

    async def start_webhook(self, url: str, port: int = 8443) -> None:
        """Start the bot in webhook mode."""
        if not self._app:
            await self.initialize()
        assert self._app is not None
        await self._app.start_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=self.token,
            webhook_url=f"{url}/{self.token}",
        )
        logger.info("telegram_webhook_started", url=url, port=port)

    async def stop(self) -> None:
        """Stop the bot."""
        if self._app:
            await self._app.stop()
            await self._app.shutdown()

    # ── Command Handlers ────────────────────────────────────────

    async def _handle_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /start command."""
        if not update.message:
            return

        welcome = (
            "🤖 **SUPERAGENT** is ready.\n\n"
            "I'm your AI agent system combining multi-agent orchestration "
            "with self-improving intelligence.\n\n"
            "**Commands:**\n"
            "/status — System status\n"
            "/task — Create a task\n"
            "/report — Generate a report\n"
            "/skills — List available skills\n"
            "/help — Show this help\n\n"
            "Or just send me a message and I'll route it to the right team."
        )
        await update.message.reply_text(welcome, parse_mode="Markdown")

    async def _handle_help(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /help command."""
        if not update.message:
            return

        help_text = (
            "🔧 **How SUPERAGENT works:**\n\n"
            "1. You send a message\n"
            "2. The Queen analyzes and routes it to the right swarm:\n"
            "   📊 **Market Swarm** — prices, trends, financial analysis\n"
            "   🔍 **Info Swarm** — research, fact-checking, summaries\n"
            "   📋 **Coord Swarm** — scheduling, alerts, coordination\n"
            "3. The swarm processes your request\n"
            "4. Results are delivered back to you\n\n"
            "**Tips:**\n"
            "• Be specific: 'Analyze AAPL stock' > 'stocks'\n"
            "• Request reports: '/report AAPL, MSFT, GOOGL'\n"
            "• Set reminders: 'Remind me to check earnings at 4pm'\n"
            "• Ask for research: 'Research semiconductor supply chain'"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def _handle_status(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /status command."""
        if not update.message:
            return

        status = self.router.get_stats()
        queen_status = {}
        if self.router._queen:
            queen_status = await self.router._queen.get_status()

        status_text = (
            "📊 **SUPERAGENT Status**\n\n"
            f"📨 Messages received: {status['messages_received']}\n"
            f"✅ Messages processed: {status['messages_processed']}\n"
            f"❌ Errors: {status['errors']}\n"
            f"💬 Active sessions: {status['active_sessions']}\n"
            f"⏱ Uptime: {status['uptime_seconds']:.0f}s\n"
        )

        if queen_status:
            status_text += "\n**Swarms:**\n"
            for name, info in queen_status.get("swarms", {}).items():
                status_text += f"  • {name}: {info['status']} ({info['run_count']} runs)\n"

        await update.message.reply_text(status_text, parse_mode="Markdown")

    async def _handle_task(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /task command — create a task via the coordination swarm."""
        if not update.message or not update.message.text:
            return

        # Extract task description (everything after /task)
        task_text = update.message.text.replace("/task", "").strip()
        if not task_text:
            await update.message.reply_text(
                "Usage: /task <description>\n"
                "Example: /task Research Q2 earnings for tech sector",
            )
            return

        # Process through router
        inbound = self._build_inbound(update, task_text)
        response = await self.router.handle_message(inbound)
        if response:
            await self._deliver_message(response)

    async def _handle_report(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /report command — generate a market report."""
        if not update.message or not update.message.text:
            return

        symbols_text = update.message.text.replace("/report", "").strip()
        if not symbols_text:
            await update.message.reply_text(
                "Usage: /report <symbols>\n"
                "Example: /report AAPL, MSFT, GOOGL",
            )
            return

        task = f"Generate a market intelligence report for: {symbols_text}"
        inbound = self._build_inbound(update, task)
        response = await self.router.handle_message(inbound)
        if response:
            await self._deliver_message(response)

    async def _handle_skills(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /skills command — list available skills."""
        if not update.message:
            return

        skills_text = "📚 **Available Skills**\n\n"

        if self.router._queen and hasattr(self.router._queen, "_swarms"):
            for name, swarm in self.router._queen._swarms.items():
                skills_text += f"**{name.value.title()} Swarm:**\n"
                for tool_name in swarm.tools:
                    skills_text += f"  • {tool_name}\n"
                skills_text += "\n"

        await update.message.reply_text(skills_text, parse_mode="Markdown")

    async def _handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        if not query:
            return

        await query.answer()
        data = query.data or ""

        if data.startswith("approve:"):
            task_id = data.split(":")[1]
            await query.edit_message_text(f"✅ Task {task_id} approved.")
        elif data.startswith("reject:"):
            task_id = data.split(":")[1]
            await query.edit_message_text(f"❌ Task {task_id} rejected.")

    # ── Message Handlers ────────────────────────────────────────

    async def _handle_text(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle regular text messages."""
        if not update.message or not update.message.text:
            return

        inbound = self._build_inbound(update, update.message.text)

        # Show typing indicator
        await update.message.chat.send_action("typing")

        response = await self.router.handle_message(inbound)
        if response:
            await self._deliver_message(response)

    async def _handle_media(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle media messages (photos, documents, voice)."""
        if not update.message:
            return

        # Extract media info
        media_info: dict[str, Any] = {}
        caption = update.message.caption or ""

        if update.message.photo:
            photo = update.message.photo[-1]  # highest resolution
            media_info["type"] = "photo"
            media_info["file_id"] = photo.file_id
            caption = caption or "Describe this image"
        elif update.message.document:
            media_info["type"] = "document"
            media_info["file_id"] = update.message.document.file_id
            media_info["filename"] = update.message.document.file_name
            caption = caption or f"Process this document: {media_info.get('filename', 'unknown')}"
        elif update.message.voice:
            media_info["type"] = "voice"
            media_info["file_id"] = update.message.voice.file_id
            caption = caption or "Transcribe this voice message"

        inbound = self._build_inbound(update, caption)
        inbound.media = media_info

        await update.message.chat.send_action("typing")

        response = await self.router.handle_message(inbound)
        if response:
            await self._deliver_message(response)

    # ── Message Delivery ────────────────────────────────────────

    async def _deliver_message(self, message: OutboundMessage) -> None:
        """Deliver an outbound message to Telegram."""
        if not self._app or not self._app.bot:
            logger.error("telegram_not_initialized")
            return

        try:
            parse_mode = None
            if message.format == "markdown":
                parse_mode = "Markdown"
            elif message.format == "html":
                parse_mode = "HTML"

            # Split long messages (Telegram limit: 4096 chars)
            content = message.content
            while content:
                chunk = content[:4096]
                content = content[4096:]

                await self._app.bot.send_message(
                    chat_id=message.chat_id,
                    text=chunk,
                    parse_mode=parse_mode,
                    reply_to_message_id=int(message.reply_to) if message.reply_to else None,
                )

            logger.info(
                "telegram_message_delivered",
                chat_id=message.chat_id,
                length=len(message.content),
            )

        except Exception as e:
            logger.error("telegram_delivery_failed", error=str(e))
            # Fallback: send without markdown
            try:
                await self._app.bot.send_message(
                    chat_id=message.chat_id,
                    text=message.content[:4096],
                )
            except Exception as e2:
                logger.error("telegram_fallback_failed", error=str(e2))

    # ── Helpers ─────────────────────────────────────────────────

    def _build_inbound(self, update: Update, content: str) -> InboundMessage:
        """Build an InboundMessage from a Telegram Update."""
        assert update.message is not None
        assert update.effective_user is not None
        assert update.effective_chat is not None

        return InboundMessage(
            channel=Channel.TELEGRAM,
            channel_message_id=str(update.message.message_id),
            user_id=str(update.effective_user.id),
            chat_id=str(update.effective_chat.id),
            content=content,
            metadata={
                "username": update.effective_user.username,
                "first_name": update.effective_user.first_name,
                "chat_type": update.effective_chat.type,
            },
        )
