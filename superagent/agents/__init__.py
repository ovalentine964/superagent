"""
SUPERAGENT Agent System

Architecture:
- Queen: Master orchestrator that routes tasks to swarms
- Market Swarm: Market intelligence (prices, trends, analysis)
- Info Swarm: Information network (research, fact-checking, summarization)
- Coord Swarm: Coordination engine (scheduling, alerts, multi-agent orchestration)

Inspired by OpenClaw's sub-agent orchestration and Hermes's Kanban task board.
"""

from agents.base_agent import BaseAgent, AgentContext, AgentResult
from agents.queen import QueenOrchestrator
from agents.market_swarm import MarketSwarm
from agents.info_swarm import InfoSwarm
from agents.coord_swarm import CoordSwarm

__all__ = [
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "QueenOrchestrator",
    "MarketSwarm",
    "InfoSwarm",
    "CoordSwarm",
]
