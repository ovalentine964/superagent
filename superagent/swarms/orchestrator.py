"""Queen Orchestrator - Routes tasks to specialized swarms.""" 
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("superagent.queen")


class SwarmType(Enum):
    MARKET_INTEL = "market_intelligence"
    INFO_NETWORK = "information_network"
    COORDINATION = "coordination_engine"
    DIRECT = "direct_response"


@dataclass
class AgentTask:
    task_id: str
    swarm: SwarmType
    intent: str
    message: str
    context: dict = field(default_factory=dict)
    priority: int = 1
    status: str = "pending"
    result: Any = None


class QueenOrchestrator:
    """Central orchestrator that classifies intent and routes to swarms."""

    def __init__(self, config=None):
        self.config = config or {}
        self.swarms = {s: [] for s in SwarmType}
        self.memory = None
        self.learning = None

    def register_agent(self, swarm, agent):
        self.swarms[swarm].append(agent)
        logger.info(f"Registered {agent.name} in {swarm.value}")

    async def classify_intent(self, message, context=None):
        msg = message.lower()
        if any(k in msg for k in ["price", "cost", "how much", "bei"]):
            return SwarmType.INFO_NETWORK
        if any(k in msg for k in ["sell", "buy", "customer", "market", "soko"]):
            return SwarmType.MARKET_INTEL
        if any(k in msg for k in ["group", "bulk", "transport", "pool", "chama"]):
            return SwarmType.COORDINATION
        return SwarmType.DIRECT

    async def handle_message(self, user_id, message):
        context = {}
        if self.memory:
            context = await self.memory.get_user_context(user_id)
        swarm = await self.classify_intent(message, context)
        task = AgentTask(
            task_id=f"task-{hash(message) % 10000}",
            swarm=swarm, intent=message, message=message, context=context,
        )
        agents = self.swarms.get(swarm, [])
        if not agents:
            return "I can help with that. What specifically do you need?"
        agent = agents[0]
        try:
            result = await agent.execute(task)
            if self.memory:
                await self.memory.store_interaction(user_id, message, result)
            return result.get("response", str(result)) if isinstance(result, dict) else str(result)
        except Exception as e:
            logger.error(f"Task failed: {e}")
            return "Something went wrong. Please try again."


queen = QueenOrchestrator()
