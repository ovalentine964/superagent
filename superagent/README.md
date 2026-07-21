# SUPERAGENT

> **An AI agent system merging OpenClaw's multi-agent orchestration with Hermes's self-improving learning loop.**

SUPERAGENT is a production-grade, self-hosted AI agent platform that combines:

- **OpenClaw's** hub-and-spoke gateway model, multi-agent isolation, sub-agent spawning, and multi-channel messaging (Telegram, Discord, API)
- **Hermes Agent's** autonomous skill creation, skill self-improvement, memory curation nudges, and FTS5 session search
- **LangGraph** for structured agent orchestration flows
- **LiteLLM** for multi-provider LLM access (Anthropic, OpenAI, Google, Ollama, etc.)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SUPERAGENT System                             │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Gateway   │  │ Queen    │  │ Memory   │  │ Learning     │   │
│  │ (Router)  │→ │ (Routes) │→ │ (Store)  │  │ Engine       │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘   │
│       ↕              ↕              ↕              ↕            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Swarm Layer                                  │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │  │
│  │  │ Market   │  │ Info     │  │ Coord    │               │  │
│  │  │ Swarm    │  │ Swarm    │  │ Swarm    │               │  │
│  │  └──────────┘  └──────────┘  └──────────┘               │  │
│  └──────────────────────────────────────────────────────────┘  │
│       ↕              ↕              ↕                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Tool     │  │ ChromaDB │  │ Redis    │  │ SQLite   │      │
│  │ Registry │  │ (Vectors)│  │ (Cache)  │  │ (FTS5)   │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
     ↕              ↕              ↕
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Telegram │ │ Discord  │ │ REST API │
│ Bot      │ │ Bot      │ │ (OpenAI) │
└──────────┘ └──────────┘ └──────────┘
```

## Quick Start

### 1. Clone and Configure

```bash
cd superagent
cp .env.example .env
# Edit .env with your API keys
```

### 2. Docker (Recommended)

```bash
docker-compose up -d
```

This starts:
- **SUPERAGENT** app (API on port 8080)
- **Redis** (caching/pub-sub on port 6379)
- **ChromaDB** (vector store on port 8000)

### 3. Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start infrastructure (Redis + ChromaDB)
docker-compose up -d redis chromadb

# Run SUPERAGENT
python -m superagent.main
```

## Components

### Agents

| Agent | Purpose | Model |
|-------|---------|-------|
| **Queen** | Master orchestrator — routes tasks to swarms | claude-sonnet-4 |
| **Market Swarm** | Prices, trends, financial analysis | claude-sonnet-4 |
| **Info Swarm** | Research, fact-checking, summarization | claude-sonnet-4 |
| **Coord Swarm** | Scheduling, alerts, coordination | gpt-4o-mini |

### Memory System

| Layer | Source | Purpose |
|-------|--------|---------|
| **Workspace** | OpenClaw | AGENTS.md, MEMORY.md, daily notes |
| **Vector** | ChromaDB | RAG — semantic search over documents |
| **Session Search** | Hermes FTS5 | Full-text search over conversation history |
| **Learning** | Hermes | Auto-curation, skill creation, memory nudges |

### Tools

| Tool | Category | Description |
|------|----------|-------------|
| `market_data` | Market | Real-time/historical market data |
| `market_search` | Market | Search for financial instruments |
| `technical_indicators` | Market | SMA, EMA, RSI, MACD, Bollinger |
| `send_message` | Communication | Send to any channel |
| `notification_sender` | Communication | Alerts with severity levels |
| `webhook_dispatch` | Communication | External webhook delivery |
| `task_board` | Coordination | Kanban-style task management |

### Gateway

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | OpenAI-compatible chat (streaming) |
| `/v1/models` | GET | List available models |
| `/v1/tasks` | POST | Create async task |
| `/v1/tasks/{id}` | GET | Get task status |
| `/health` | GET | Health check |
| `/status` | GET | System status |

## Configuration

### config.yaml

Main configuration file with sections for:
- `system` — Name, version, directories
- `llm` — Model selection (default, fallback, fast)
- `agents` — Swarm configuration (workers, tools)
- `memory` — Workspace, vector, session search, learning
- `gateway` — Channels (Telegram, Discord, API)
- `tools` — Tool registry and market data providers
- `cron` — Scheduling configuration
- `security` — Sandboxing, approval, rate limits

### Environment Variables

See `.env.example` for all available variables. Key ones:

- `ANTHROPIC_API_KEY` — Anthropic API key
- `OPENAI_API_KEY` — OpenAI API key
- `TELEGRAM_BOT_TOKEN` — Telegram bot token
- `API_AUTH_TOKEN` — API authentication token

## Learning Loop

SUPERAGENT continuously improves through the Hermes learning loop:

1. **Auto-Skill Creation** — When a task requires 5+ tool calls or recovers from an error, a reusable skill is automatically created
2. **Skill Self-Improvement** — When a better path is discovered during execution, the skill is patched
3. **Memory Curation** — Periodic nudges ask the LLM if anything is worth remembering long-term
4. **Session Search** — FTS5 full-text search over all conversation history for episodic recall

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio ruff

# Run tests
pytest

# Lint
ruff check .

# Type check
mypy agents/ memory/ tools/ gateway/ data/
```

## License

MIT
