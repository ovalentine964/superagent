"""
Base Agent — Foundation class for all SUPERAGENT agents.

Combines:
- OpenClaw's session management and tool execution model
- Hermes's self-improving learning loop (auto skill creation, memory curation)
- LangGraph for structured agent loops
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

logger = structlog.get_logger()


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"


@dataclass
class AgentContext:
    """Context passed to an agent for a single task execution."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str | None = None
    channel: str | None = None
    parent_task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    workspace_path: Path = field(default_factory=lambda: Path("./workspace"))
    memory_path: Path = field(default_factory=lambda: Path("./workspace/memory"))


@dataclass
class ToolCall:
    """A tool invocation requested by the agent."""

    tool_name: str
    arguments: dict[str, Any]
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ToolResult:
    """Result from a tool execution."""

    call_id: str
    tool_name: str
    output: Any
    success: bool = True
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class AgentResult:
    """Final result from an agent execution."""

    task_id: str
    agent_id: str
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    tokens_used: int = 0
    created_skills: list[str] = field(default_factory=list)
    memory_updates: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """
    Base class for all SUPERAGENT agents.

    Provides:
    - LLM inference via LiteLLM (multi-provider)
    - Tool execution with result handling
    - Memory read/write (workspace files + vector store)
    - Self-improvement loop (Hermes pattern)
    - Session persistence
    - Observability via structlog
    """

    def __init__(
        self,
        agent_id: str,
        model: str = "openrouter/anthropic/claude-sonnet-4",
        tools: list[str] | None = None,
        workspace_path: str = "./workspace",
    ):
        self.agent_id = agent_id
        self.model = model
        self.tools = tools or []
        self.workspace_path = Path(workspace_path)
        self.status = AgentStatus.IDLE
        self._session_history: list[BaseMessage] = []
        self._tool_registry: dict[str, Callable] = {}
        self._run_count = 0

        # Learning loop state
        self._tool_call_count = 0
        self._error_recoveries = 0
        self._user_corrections = 0

    async def initialize(self) -> None:
        """Load workspace context and register available tools."""
        await self._load_workspace_context()
        await self._register_tools()
        logger.info("agent_initialized", agent_id=self.agent_id, tools=len(self._tool_registry))

    async def _load_workspace_context(self) -> None:
        """Load AGENTS.md, SOUL.md, USER.md as system context (OpenClaw pattern)."""
        context_parts = []
        for filename in ("AGENTS.md", "SOUL.md", "USER.md"):
            path = self.workspace_path / filename
            if path.exists():
                content = path.read_text(encoding="utf-8")
                context_parts.append(f"## {filename}\n{content}")

        if context_parts:
            system_context = "\n\n---\n\n".join(context_parts)
            self._session_history.insert(0, SystemMessage(content=system_context))

    async def _register_tools(self) -> None:
        """Register tools from the tool registry. Override in subclasses."""
        # Imported lazily to avoid circular imports
        from tools.registry import ToolRegistry

        registry = ToolRegistry.get_instance()
        for tool_name in self.tools:
            tool = registry.get(tool_name)
            if tool:
                self._tool_registry[tool_name] = tool

    def get_system_prompt(self) -> str:
        """Build the system prompt. Override in subclasses for specialized behavior."""
        tool_descriptions = "\n".join(
            f"- {name}: {getattr(fn, 'description', 'No description')}"
            for name, fn in self._tool_registry.items()
        )
        return (
            f"You are {self.agent_id}, a specialized agent in the SUPERAGENT system.\n"
            f"Available tools:\n{tool_descriptions}\n\n"
            f"Think step by step. Use tools when needed. Be precise and factual."
        )

    async def run(
        self,
        task: str,
        context: AgentContext | None = None,
    ) -> AgentResult:
        """
        Execute a task through the agent loop.

        Flow:
        1. Assemble context (system prompt + memory + task)
        2. Call LLM
        3. If tool calls → execute tools → feed results back → loop
        4. Return final result
        5. Run learning loop (if conditions met)
        """
        if context is None:
            context = AgentContext()

        start_time = time.monotonic()
        self.status = AgentStatus.RUNNING
        self._run_count += 1
        total_tokens = 0

        try:
            # Build message list
            messages: list[BaseMessage] = [
                SystemMessage(content=self.get_system_prompt()),
                *self._get_memory_context(),
                *self._session_history[-20:],  # last 20 messages for context
                HumanMessage(content=task),
            ]

            result_content = ""
            all_tool_calls: list[ToolCall] = []
            all_tool_results: list[ToolResult] = []

            # Agent loop (max 10 iterations to prevent runaway)
            for iteration in range(10):
                response = await self._call_llm(messages)
                total_tokens += response.get("usage", {}).get("total_tokens", 0)

                message = response["message"]
                messages.append(message)

                # Check for tool calls
                tool_calls = self._extract_tool_calls(message)
                if not tool_calls:
                    result_content = message.content or ""
                    break

                # Execute tools
                for tc in tool_calls:
                    all_tool_calls.append(tc)
                    tool_result = await self._execute_tool(tc)
                    all_tool_results.append(tool_result)
                    self._tool_call_count += 1

                    # Feed result back to LLM
                    messages.append(
                        AIMessage(
                            content="",
                            tool_calls=[{
                                "id": tc.call_id,
                                "name": tc.tool_name,
                                "arguments": json.dumps(tc.arguments),
                            }],
                        )
                    )
                    messages.append(
                        HumanMessage(
                            content=f"Tool result for {tc.tool_name}: {json.dumps(tool_result.output)}"
                        )
                    )

            duration_ms = (time.monotonic() - start_time) * 1000

            # Update session history
            self._session_history.append(HumanMessage(content=task))
            self._session_history.append(AIMessage(content=result_content))

            result = AgentResult(
                task_id=context.task_id,
                agent_id=self.agent_id,
                content=result_content,
                tool_calls=all_tool_calls,
                tool_results=all_tool_results,
                duration_ms=duration_ms,
                tokens_used=total_tokens,
            )

            # Hermes-style learning loop
            await self._learning_loop(task, result)

            self.status = AgentStatus.IDLE
            return result

        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error("agent_run_failed", agent_id=self.agent_id, error=str(e))
            raise

    async def _call_llm(self, messages: list[BaseMessage]) -> dict[str, Any]:
        """Call the LLM via LiteLLM."""
        import litellm

        formatted = self._format_messages(messages)
        tools_schema = self._build_tools_schema()

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": formatted,
            "max_tokens": 4096,
        }
        if tools_schema:
            kwargs["tools"] = tools_schema

        response = await litellm.acompletion(**kwargs)
        choice = response.choices[0]

        return {
            "message": choice.message,
            "usage": {
                "total_tokens": getattr(response.usage, "total_tokens", 0) if response.usage else 0,
            },
        }

    def _format_messages(self, messages: list[BaseMessage]) -> list[dict]:
        """Convert LangChain messages to LiteLLM format."""
        formatted = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                formatted.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                formatted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                entry: dict[str, Any] = {"role": "assistant", "content": msg.content}
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    entry["tool_calls"] = msg.tool_calls
                formatted.append(entry)
            else:
                formatted.append({"role": "user", "content": str(msg.content)})
        return formatted

    def _build_tools_schema(self) -> list[dict]:
        """Build OpenAI-compatible tool schemas from registered tools."""
        schemas = []
        for name, tool_fn in self._tool_registry.items():
            schema = getattr(tool_fn, "schema", None)
            if schema:
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": getattr(tool_fn, "description", ""),
                        "parameters": schema,
                    },
                })
        return schemas

    def _extract_tool_calls(self, message: Any) -> list[ToolCall]:
        """Extract tool calls from an LLM response message."""
        calls = []
        raw_calls = getattr(message, "tool_calls", None) or []
        for tc in raw_calls:
            args = tc.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            calls.append(ToolCall(
                tool_name=tc["name"],
                arguments=args,
                call_id=tc.get("id", str(uuid.uuid4())),
            ))
        return calls

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call."""
        tool_fn = self._tool_registry.get(tool_call.tool_name)
        if not tool_fn:
            return ToolResult(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                output=None,
                success=False,
                error=f"Tool '{tool_call.tool_name}' not found in registry",
            )

        start = time.monotonic()
        try:
            if asyncio.iscoroutinefunction(tool_fn):
                output = await tool_fn(**tool_call.arguments)
            else:
                output = tool_fn(**tool_call.arguments)
            duration = (time.monotonic() - start) * 1000
            return ToolResult(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                output=output,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            self._error_recoveries += 1
            return ToolResult(
                call_id=tool_call.call_id,
                tool_name=tool_call.tool_name,
                output=None,
                success=False,
                error=str(e),
                duration_ms=duration,
            )

    def _get_memory_context(self) -> list[SystemMessage]:
        """
        Load memory context (OpenClaw workspace pattern).
        Reads MEMORY.md for long-term memory.
        """
        memory_file = self.workspace_path / "MEMORY.md"
        if memory_file.exists():
            content = memory_file.read_text(encoding="utf-8")
            if content.strip():
                return [SystemMessage(content=f"## Long-term Memory\n{content}")]
        return []

    # ── Learning Loop (Hermes Pattern) ──────────────────────────────

    async def _learning_loop(self, task: str, result: AgentResult) -> None:
        """
        Hermes-inspired learning loop:
        1. Auto-skill creation if workflow was complex
        2. Memory curation nudge
        3. Skill improvement if better path discovered
        """
        # Auto-create skill if task was complex enough
        if self._should_create_skill(result):
            skill_name = await self._auto_create_skill(task, result)
            if skill_name:
                result.created_skills.append(skill_name)
                logger.info("auto_skill_created", agent_id=self.agent_id, skill=skill_name)

        # Memory curation nudge (periodic)
        if self._run_count % 10 == 0:  # every 10 runs
            memory_update = await self._memory_curation_nudge(task, result)
            if memory_update:
                result.memory_updates.append(memory_update)

    def _should_create_skill(self, result: AgentResult) -> bool:
        """
        Decide whether to auto-create a skill (Hermes triggers):
        - 5+ tool calls in the workflow
        - Recovery from an error
        - Complex multi-step task
        """
        if len(result.tool_calls) >= 5:
            return True
        if any(not tr.success for tr in result.tool_results):
            return True
        return False

    async def _auto_create_skill(self, task: str, result: AgentResult) -> str | None:
        """Create a reusable skill from a successful workflow."""
        skill_name = f"auto_{self.agent_id}_{int(time.time())}"
        skill_dir = self.workspace_path / "skills" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Build skill content
        tool_sequence = []
        for tc, tr in zip(result.tool_calls, result.tool_results):
            step = {
                "tool": tc.tool_name,
                "args": tc.arguments,
                "success": tr.success,
            }
            tool_sequence.append(step)

        skill_content = f"""---
name: {skill_name}
description: "Auto-generated skill from task: {task[:100]}"
metadata:
  superagent:
    auto_created: true
    agent_id: {self.agent_id}
    created_at: {time.strftime("%Y-%m-%d %H:%M:%S")}
---

# {skill_name}

## Task
{task}

## Steps
"""
        for i, step in enumerate(tool_sequence, 1):
            status = "✅" if step["success"] else "❌"
            skill_content += f"\n{i}. {status} Use `{step['tool']}` with `{json.dumps(step['args'])}`"

        skill_content += f"\n\n## Result\n{result.content[:500]}"

        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        return skill_name

    async def _memory_curation_nudge(self, task: str, result: AgentResult) -> str | None:
        """
        Hermes-style periodic memory nudge:
        Ask the LLM if anything is worth remembering long-term.
        """
        import litellm

        nudge_prompt = (
            "Review this task and result. Is anything worth remembering long-term?\n"
            "If yes, output a single concise memory entry. If no, output 'NONE'.\n\n"
            f"Task: {task}\n"
            f"Result: {result.content[:1000]}"
        )

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": nudge_prompt}],
                max_tokens=200,
            )
            memory_entry = response.choices[0].message.content.strip()
            if memory_entry and memory_entry != "NONE":
                await self._write_memory(memory_entry)
                return memory_entry
        except Exception as e:
            logger.warning("memory_nudge_failed", error=str(e))
        return None

    async def _write_memory(self, entry: str) -> None:
        """Append a memory entry to the daily memory file."""
        daily_file = self.workspace_path / "memory" / f"{time.strftime('%Y-%m-%d')}.md"
        daily_file.parent.mkdir(parents=True, exist_ok=True)

        existing = ""
        if daily_file.exists():
            existing = daily_file.read_text(encoding="utf-8")

        timestamp = time.strftime("%H:%M")
        new_entry = f"\n\n### [{timestamp}] {self.agent_id}\n{entry}\n"
        daily_file.write_text(existing + new_entry, encoding="utf-8")
        logger.info("memory_written", agent_id=self.agent_id, file=str(daily_file))

    def clear_session(self) -> None:
        """Clear session history (for new conversations)."""
        self._session_history.clear()
