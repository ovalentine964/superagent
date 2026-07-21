"""
SUPERAGENT Tools System

MCP-compatible tool registry with:
- Dynamic tool discovery
- Tool schemas (OpenAI function calling format)
- Tool execution with timeout and error handling
- Built-in tools: market data, web search, communication
"""

from tools.registry import ToolRegistry
from tools.market_tools import register_market_tools
from tools.communication_tools import register_communication_tools

__all__ = ["ToolRegistry", "register_market_tools", "register_communication_tools"]
