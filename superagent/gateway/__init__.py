"""
SUPERAGENT Gateway

Multi-channel message routing:
- Telegram bot handler
- OpenAI-compatible REST API
- Webhook receiver
- Message router with session management
"""

from gateway.router import MessageRouter
from gateway.api_server import create_app

__all__ = ["MessageRouter", "create_app"]
