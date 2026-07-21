"""
Tool Registry — MCP-compatible tool management

Inspired by:
- OpenClaw's tool system (typed schemas, sandboxing, allowlists)
- Hermes's tool registry (self-registering tools, 70+ built-in)

Provides:
- Tool registration with schemas
- Tool discovery (auto-discover from modules)
- Tool execution with timeout and error handling
- OpenAI function calling format compatibility
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import structlog

logger = structlog.get_logger()


@dataclass
class ToolDefinition:
    """Definition of a registered tool."""

    name: str
    description: str
    function: Callable
    parameters: dict[str, Any]  # JSON Schema
    category: str = "general"
    timeout_seconds: int = 300
    requires_approval: bool = False
    enabled: bool = True

    @property
    def schema(self) -> dict[str, Any]:
        """OpenAI-compatible function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """
    Central tool registry for SUPERAGENT.

    Features:
    - Singleton pattern for global access
    - Tool registration with auto-schema generation
    - Module-based tool discovery
    - MCP-compatible tool format
    - Execution with timeout and error handling
    """

    _instance: ToolRegistry | None = None

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    @classmethod
    def get_instance(cls) -> ToolRegistry:
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None

    def register(
        self,
        name: str,
        description: str,
        function: Callable,
        parameters: dict[str, Any],
        category: str = "general",
        timeout_seconds: int = 300,
        requires_approval: bool = False,
    ) -> ToolDefinition:
        """Register a tool."""
        tool = ToolDefinition(
            name=name,
            description=description,
            function=function,
            parameters=parameters,
            category=category,
            timeout_seconds=timeout_seconds,
            requires_approval=requires_approval,
        )
        self._tools[name] = tool
        logger.info("tool_registered", name=name, category=category)
        return tool

    def register_decorator(
        self,
        name: str | None = None,
        description: str | None = None,
        category: str = "general",
        timeout_seconds: int = 300,
    ) -> Callable:
        """
        Decorator for registering tools.

        Usage:
            @registry.register_decorator(name="my_tool", description="Does something")
            async def my_tool(param: str) -> str:
                return f"Result: {param}"
        """

        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_desc = description or func.__doc__ or f"Tool: {tool_name}"
            parameters = self._infer_schema(func)

            self.register(
                name=tool_name,
                description=tool_desc,
                function=func,
                parameters=parameters,
                category=category,
                timeout_seconds=timeout_seconds,
            )
            return func

        return decorator

    def get(self, name: str) -> ToolDefinition | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: str | None = None) -> list[ToolDefinition]:
        """List all registered tools, optionally filtered by category."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return [t for t in tools if t.enabled]

    def get_schemas(self, tool_names: list[str] | None = None) -> list[dict[str, Any]]:
        """Get OpenAI-compatible schemas for specified tools."""
        tools = self._tools.values()
        if tool_names:
            tools = [t for t in tools if t.name in tool_names]
        return [t.schema for t in tools if t.enabled]

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Execute a tool by name."""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found in registry")

        if not tool.enabled:
            raise ValueError(f"Tool '{name}' is disabled")

        start = time.monotonic()
        try:
            if asyncio.iscoroutinefunction(tool.function):
                result = await asyncio.wait_for(
                    tool.function(**arguments),
                    timeout=tool.timeout_seconds,
                )
            else:
                result = tool.function(**arguments)

            duration = (time.monotonic() - start) * 1000
            logger.info("tool_executed", name=name, duration_ms=duration)
            return result

        except asyncio.TimeoutError:
            logger.error("tool_timeout", name=name, timeout=tool.timeout_seconds)
            raise TimeoutError(f"Tool '{name}' timed out after {tool.timeout_seconds}s")
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            logger.error("tool_failed", name=name, error=str(e), duration_ms=duration)
            raise

    async def discover_modules(self, tool_dirs: list[str]) -> int:
        """
        Auto-discover and register tools from module directories.

        Looks for Python files with a `register(registry)` function.
        """
        count = 0
        for tool_dir in tool_dirs:
            path = Path(tool_dir)
            if not path.exists():
                continue

            for py_file in path.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                try:
                    module_name = py_file.stem
                    spec = importlib.util.spec_from_file_location(
                        f"tools.{module_name}", str(py_file)
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        if hasattr(module, "register"):
                            module.register(self)
                            count += 1
                            logger.info("tool_module_discovered", module=module_name)
                except Exception as e:
                    logger.warning("tool_module_failed", file=str(py_file), error=str(e))

        return count

    def _infer_schema(self, func: Callable) -> dict[str, Any]:
        """Infer JSON Schema from function signature."""
        sig = inspect.signature(func)
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = "string"  # default
            if param.annotation != inspect.Parameter.empty:
                param_type = type_map.get(param.annotation, "string")

            properties[param_name] = {"type": param_type}

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }
