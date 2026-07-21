"""
Message Router — Unified message routing across channels

Inspired by:
- OpenClaw's gateway hub-and-spoke model (single process, all channels)
- Hermes's session-tied routing (sessions tied to IDs, not platforms)

Routes inbound messages from any channel through:
1. Access control (allowlists, auth)
2. Session resolution (user → session mapping)
3. Agent dispatch (Queen → Swarm → Response)
4. Response delivery (back to originating channel)
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger()


class Channel(str, Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    API = "api"
    WEBHOOK = "webhook"


@dataclass
class InboundMessage:
    """A message received from any channel."""

    channel: Channel
    channel_message_id: str
    user_id: str
    chat_id: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    media: dict[str, Any] | None = None  # images, audio, video, documents

    @property
    def session_key(self) -> str:
        """Unique session key for this user+channel+chat combination."""
        return f"{self.channel.value}:{self.user_id}:{self.chat_id}"


@dataclass
class OutboundMessage:
    """A message to deliver to a channel."""

    channel: Channel
    chat_id: str
    content: str
    format: str = "text"  # text, markdown, html
    reply_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """A conversation session."""

    session_key: str
    user_id: str
    channel: Channel
    chat_id: str
    agent_id: str = "queen"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    message_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class MessageRouter:
    """
    Central message router for SUPERAGENT.

    Routes messages from all channels through a unified pipeline:
    1. Auth/access control
    2. Session resolution
    3. Agent dispatch (Queen orchestrator)
    4. Response delivery

    Inspired by OpenClaw's Gateway and Hermes's session routing.
    """

    def __init__(
        self,
        allowed_users: dict[str, list[str]] | None = None,
    ):
        # Channel handlers (registered at startup)
        self._channel_handlers: dict[Channel, Callable[..., Coroutine]] = {}

        # Session store
        self._sessions: dict[str, Session] = {}

        # Access control
        self._allowed_users = allowed_users or {}  # channel → [user_ids]

        # Agent reference (set during initialization)
        self._queen: Any = None

        # Message processors (middleware chain)
        self._processors: list[Callable[[InboundMessage], Coroutine]] = []

        # Stats
        self._stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "errors": 0,
            "start_time": time.time(),
        }

    def set_queen(self, queen: Any) -> None:
        """Set the Queen orchestrator reference."""
        self._queen = queen

    def register_channel(
        self,
        channel: Channel,
        handler: Callable[..., Coroutine],
    ) -> None:
        """Register a channel handler."""
        self._channel_handlers[channel] = handler
        logger.info("channel_registered", channel=channel.value)

    def add_processor(self, processor: Callable[[InboundMessage], Coroutine]) -> None:
        """Add a message processor (middleware)."""
        self._processors.append(processor)

    def set_allowed_users(self, channel: str, user_ids: list[str]) -> None:
        """Set allowed users for a channel."""
        self._allowed_users[channel] = user_ids

    # ── Message Processing Pipeline ─────────────────────────────

    async def handle_message(self, message: InboundMessage) -> OutboundMessage | None:
        """
        Process an inbound message through the full pipeline.

        Returns the response message, or None if no response needed.
        """
        self._stats["messages_received"] += 1

        try:
            # Step 1: Access control
            if not self._check_access(message):
                logger.warning(
                    "access_denied",
                    channel=message.channel.value,
                    user_id=message.user_id,
                )
                return OutboundMessage(
                    channel=message.channel,
                    chat_id=message.chat_id,
                    content="Access denied. Please contact the administrator.",
                )

            # Step 2: Apply middleware processors
            for processor in self._processors:
                processed = await processor(message)
                if processed is None:
                    return None  # processor consumed the message
                if isinstance(processed, OutboundMessage):
                    return processed

            # Step 3: Resolve or create session
            session = self._resolve_session(message)

            # Step 4: Dispatch to Queen
            if not self._queen:
                return OutboundMessage(
                    channel=message.channel,
                    chat_id=message.chat_id,
                    content="System not ready. Queen orchestrator not initialized.",
                )

            # Build context for the agent
            from agents.base_agent import AgentContext

            context = AgentContext(
                session_id=session.session_key,
                user_id=message.user_id,
                channel=message.channel.value,
                metadata={
                    "chat_id": message.chat_id,
                    "channel_message_id": message.channel_message_id,
                },
            )

            # Dispatch through Queen
            result = await self._queen.dispatch(message.content, context)

            # Update session
            session.updated_at = time.time()
            session.message_count += 1

            self._stats["messages_processed"] += 1

            # Step 5: Build response
            return OutboundMessage(
                channel=message.channel,
                chat_id=message.chat_id,
                content=result.content,
                format="markdown",
                metadata={
                    "task_id": result.task_id,
                    "agent_id": result.agent_id,
                    "duration_ms": result.duration_ms,
                    "tokens_used": result.tokens_used,
                },
            )

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(
                "message_handling_failed",
                error=str(e),
                channel=message.channel.value,
                user_id=message.user_id,
            )
            return OutboundMessage(
                channel=message.channel,
                chat_id=message.chat_id,
                content=f"An error occurred: {str(e)[:200]}",
            )

    async def deliver(self, message: OutboundMessage) -> bool:
        """Deliver an outbound message through the appropriate channel handler."""
        handler = self._channel_handlers.get(message.channel)
        if not handler:
            logger.error("no_handler", channel=message.channel.value)
            return False

        try:
            await handler(message)
            return True
        except Exception as e:
            logger.error("delivery_failed", channel=message.channel.value, error=str(e))
            return False

    # ── Access Control ──────────────────────────────────────────

    def _check_access(self, message: InboundMessage) -> bool:
        """Check if the user is allowed to send messages."""
        channel_name = message.channel.value
        allowed = self._allowed_users.get(channel_name, [])

        # Empty allowlist = allow all
        if not allowed:
            return True

        return message.user_id in allowed

    # ── Session Management ──────────────────────────────────────

    def _resolve_session(self, message: InboundMessage) -> Session:
        """Resolve or create a session for the message."""
        key = message.session_key

        if key not in self._sessions:
            self._sessions[key] = Session(
                session_key=key,
                user_id=message.user_id,
                channel=message.channel,
                chat_id=message.chat_id,
            )
            logger.info("session_created", session_key=key)

        return self._sessions[key]

    def get_session(self, session_key: str) -> Session | None:
        """Get a session by key."""
        return self._sessions.get(session_key)

    def list_sessions(self) -> list[Session]:
        """List all active sessions."""
        return list(self._sessions.values())

    # ── Stats ───────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get router statistics."""
        return {
            **self._stats,
            "active_sessions": len(self._sessions),
            "registered_channels": list(self._channel_handlers.keys()),
            "uptime_seconds": time.time() - self._stats["start_time"],
        }
