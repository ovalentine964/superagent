"""
Queen Orchestrator — Master agent that routes tasks to specialized swarms.

Inspired by:
- OpenClaw's sub-agent spawning with push-based completion
- Hermes's Kanban task board with worker lanes
- LangGraph for structured orchestration flow

The Queen analyzes incoming tasks and delegates to the appropriate swarm:
- Market Swarm: prices, trends, financial analysis
- Info Swarm: research, fact-checking, summarization
- Coord Swarm: scheduling, alerts, multi-agent coordination
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from agents.base_agent import AgentContext, AgentResult, BaseAgent

logger = structlog.get_logger()


class SwarmType(str, Enum):
    MARKET = "market"
    INFO = "info"
    COORD = "coord"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class QueenOrchestrator(BaseAgent):
    """
    The Queen — master orchestrator.

    Responsibilities:
    1. Classify incoming tasks by domain
    2. Route to the appropriate swarm
    3. Manage parallel swarm execution
    4. Aggregate results
    5. Handle cross-swarm coordination
    """

    def __init__(self, model: str = "nvidia/minimaxai/minimax-m3", **kwargs: Any):
        super().__init__(
            agent_id="queen",
            model=model,
            tools=["web_search", "task_board"],
            **kwargs,
        )
        self._swarms: dict[SwarmType, BaseAgent] = {}
        self._task_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._active_tasks: dict[str, dict[str, Any]] = {}

    async def initialize(self) -> None:
        """Initialize the Queen and all swarms."""
        await super().initialize()
        await self._initialize_swarms()
        logger.info("queen_initialized", swarms=list(self._swarms.keys()))

    async def _initialize_swarms(self) -> None:
        """Create and initialize all swarm agents."""
        from agents.coord_swarm import CoordSwarm
        from agents.info_swarm import InfoSwarm
        from agents.market_swarm import MarketSwarm

        swarm_classes = {
            SwarmType.MARKET: MarketSwarm,
            SwarmType.INFO: InfoSwarm,
            SwarmType.COORD: CoordSwarm,
        }

        for swarm_type, cls in swarm_classes.items():
            swarm = cls(workspace_path=str(self.workspace_path))
            await swarm.initialize()
            self._swarms[swarm_type] = swarm

    def get_system_prompt(self) -> str:
        return (
            "You are the QUEEN — the master orchestrator of the SUPERAGENT system.\n"
            "Your job is to analyze incoming tasks and decide which swarm handles them.\n\n"
            "Available swarms:\n"
            "- market: Prices, trends, financial analysis, market data, trading signals\n"
            "- info: Research, fact-checking, summarization, news analysis, web research\n"
            "- coord: Scheduling, alerts, reminders, multi-agent task coordination\n\n"
            "For each task, output a JSON object:\n"
            '{"swarm": "market|info|coord", "priority": "low|medium|high|critical", '
            '"subtask": "refined task description", "parallel": false}\n\n'
            "If a task spans multiple swarms, list them separated by commas.\n"
            "Be precise. Route efficiently. Minimize token waste."
        )

    async def route_task(self, task: str, context: AgentContext | None = None) -> str:
        """
        Classify a task and return the target swarm(s).

        Returns JSON string: {"swarm": "...", "priority": "...", "subtask": "..."}
        """
        import litellm

        if context is None:
            context = AgentContext()

        response = await litellm.acompletion(
            model=self.model,
            messages=[
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": f"Route this task:\n\n{task}"},
            ],
            max_tokens=200,
        )

        routing = response.choices[0].message.content.strip()
        logger.info("task_routed", task=task[:80], routing=routing)
        return routing

    async def dispatch(
        self,
        task: str,
        context: AgentContext | None = None,
    ) -> AgentResult:
        """
        Full dispatch flow:
        1. Route the task
        2. Execute on the target swarm(s)
        3. Aggregate results
        """
        if context is None:
            context = AgentContext()

        start = time.monotonic()

        # Step 1: Route
        routing_json = await self.route_task(task, context)
        routing = self._parse_routing(routing_json)

        # Step 2: Execute on swarm(s)
        swarm_type = SwarmType(routing.get("swarm", "info"))
        subtask = routing.get("subtask", task)
        priority = routing.get("priority", "medium")

        swarm = self._swarms.get(swarm_type)
        if not swarm:
            return AgentResult(
                task_id=context.task_id,
                agent_id=self.agent_id,
                content=f"Error: No swarm found for type '{swarm_type}'",
            )

        logger.info(
            "dispatching_to_swarm",
            swarm=swarm_type.value,
            priority=priority,
            subtask=subtask[:80],
        )

        # Step 3: Execute
        result = await swarm.run(subtask, context)

        # Step 4: Enrich result with routing metadata
        result.metadata["routing"] = routing
        result.metadata["queen_duration_ms"] = (time.monotonic() - start) * 1000

        return result

    async def dispatch_parallel(
        self,
        tasks: list[str],
        context: AgentContext | None = None,
    ) -> list[AgentResult]:
        """
        Dispatch multiple tasks in parallel.
        Inspired by OpenClaw's sub-agent spawning pattern.
        """
        if context is None:
            context = AgentContext()

        # Route all tasks first
        routings = await asyncio.gather(
            *[self.route_task(t, context) for t in tasks]
        )

        # Group by swarm
        swarm_tasks: dict[SwarmType, list[tuple[str, str]]] = {}
        for task, routing_json in zip(tasks, routings):
            routing = self._parse_routing(routing_json)
            swarm_type = SwarmType(routing.get("swarm", "info"))
            subtask = routing.get("subtask", task)
            if swarm_type not in swarm_tasks:
                swarm_tasks[swarm_type] = []
            swarm_tasks[swarm_type].append((subtask, routing.get("priority", "medium")))

        # Execute all in parallel
        async def _run_on_swarm(
            swarm_type: SwarmType,
            task_list: list[tuple[str, str]],
        ) -> list[AgentResult]:
            swarm = self._swarms.get(swarm_type)
            if not swarm:
                return []
            results = []
            for subtask, _priority in task_list:
                ctx = AgentContext(
                    parent_task_id=context.task_id,
                    metadata={"swarm": swarm_type.value},
                )
                result = await swarm.run(subtask, ctx)
                results.append(result)
            return results

        all_results_nested = await asyncio.gather(
            *[_run_on_swarm(st, tl) for st, tl in swarm_tasks.items()]
        )

        # Flatten
        all_results = [r for group in all_results_nested for r in group]
        return all_results

    def _parse_routing(self, routing_json: str) -> dict[str, Any]:
        """Parse the Queen's routing decision."""
        import json

        # Try to extract JSON from the response
        try:
            # Handle markdown code blocks
            clean = routing_json.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(clean)
        except (json.JSONDecodeError, IndexError):
            # Fallback: classify by keywords
            return self._keyword_classify(routing_json)

    def _keyword_classify(self, text: str) -> dict[str, Any]:
        """Fallback keyword-based classification."""
        text_lower = text.lower()

        market_keywords = ["market", "price", "stock", "trade", "forex", "crypto", "financial"]
        coord_keywords = ["schedule", "remind", "alert", "cron", "timer", "coordinate"]

        for kw in market_keywords:
            if kw in text_lower:
                return {"swarm": "market", "priority": "medium", "subtask": text}

        for kw in coord_keywords:
            if kw in text_lower:
                return {"swarm": "coord", "priority": "medium", "subtask": text}

        return {"swarm": "info", "priority": "medium", "subtask": text}

    async def get_status(self) -> dict[str, Any]:
        """Get orchestrator status."""
        return {
            "queen": {
                "status": self.status.value,
                "active_tasks": len(self._active_tasks),
                "run_count": self._run_count,
            },
            "swarms": {
                name: {
                    "status": swarm.status.value,
                    "run_count": swarm._run_count,
                }
                for name, swarm in self._swarms.items()
            },
        }
