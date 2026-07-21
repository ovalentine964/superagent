# superagent

**Merged Hermes Agent + OpenClaw — Self-Improving Multi-Agent System**

## What Is This?

A purpose-built multi-agent system that combines:
- **Hermes Agent's** self-improving learning loops, skill creation, and reflection cycles
- **OpenClaw's** gateway system, tool registry, memory architecture, and sub-agent spawning
- **Economic Intelligence Swarms** for solving marketing inefficiencies, information asymmetry, and coordination failures

## Architecture

```
                    👑 QUEEN (Orchestrator)
                   Intent → Swarm → Response
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
     🏪 Market Intel  📊 Info Network 🤝 Coordination
     Customer disc.   Price forecasts  Worker matching
     Price monitoring Demand analysis  Bulk purchasing
     Shopfronts       Knowledge base   Collective bargaining
            │             │             │
            └─────────────┼─────────────┘
                          ▼
              🧠 UNIFIED MEMORY
         Workspace files + FTS5 + ChromaDB
                          │
                          ▼
              🔄 LEARNING LOOP
         Reflection → Skill Creation → Improvement
```

## Quick Start

```bash
# Install dependencies
pip install -r superagent/requirements.txt

# Set environment
export TELEGRAM_BOT_TOKEN="your-token"
export OPENROUTER_API_KEY="your-key"

# Run
python superagent_main.py
```

## Components

| Component | Source | What It Does |
|-----------|--------|-------------|
| Queen Orchestrator | OpenClaw + new | Classifies intent, routes to swarms |
| Market Intelligence Swarm | New | Customer discovery, pricing, shopfronts |
| Information Network Swarm | New | Demand forecasting, knowledge base |
| Coordination Engine Swarm | New | Worker matching, bulk purchasing |
| Unified Memory | OpenClaw + Hermes | Workspace files + FTS5 + vector search |
| Learning Engine | Hermes | Self-improvement, skill creation, reflection |
| Tool Registry | OpenClaw + MCP | Compatible with MCP protocol |
| Gateway | OpenClaw | Telegram, API server, multi-channel |
| API Server | Hermes | OpenAI-compatible endpoint |

## Telegram Bot Commands

- Send any message → Queen routes to appropriate swarm
- `/status` — System status
- `/skills` — List learned skills
- `/task` — Create a task on the Kanban board

## API Endpoints

- `POST /v1/chat/completions` — OpenAI-compatible chat
- `GET /health` — Health check
- `GET /v1/models` — Available models

## License

MIT
