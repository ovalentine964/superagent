# SUPERAGENT

**Merged OpenClaw + Hermes Agent — Self-Improving Multi-Agent System**

<p align="center">
  <a href="https://superagent-zzgx.onrender.com/health"><img src="https://img.shields.io/badge/Status-Live-green?style=for-the-badge" alt="Status"></a>
  <a href="https://github.com/ovalentine964/superagent"><img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License"></a>
</p>

## What Is This?

A **multi-agent system** that combines:
- **OpenClaw's** gateway, tools, memory, and sub-agent spawning
- **Hermes Agent's** self-improving learning loops, skill creation, and reflection cycles
- **Economic Intelligence Swarms** for solving real-world problems

## Quick Start

```bash
# Install dependencies
pip install -r superagent/requirements.txt

# Set environment variables
export TELEGRAM_BOT_TOKEN="your-token"
export NVIDIA_API_KEY="your-key"
export TELEGRAM_CHAT_ID="your-chat-id"

# Run
python superagent_main.py
```

## Architecture

```
         QUEEN (Orchestrator)
        Intent → Swarm → Response
               │
   ┌───────────┼───────────┐
   ▼           ▼           ▼
Market Intel  Info Network  Coordination
Swarm         Swarm         Swarm
   │           │           │
   └───────────┼───────────┘
               ▼
        Unified Memory
    (SQLite + FTS5 + ChromaDB)
               │
               ▼
        Learning Loop
    (Reflection + Skill Creation)
```

## Components

| Component | Source | What It Does |
|-----------|--------|-------------|
| Queen Orchestrator | OpenClaw + New | Routes tasks to specialized swarms |
| Market Intelligence | New | Prices, customers, shopfronts |
| Information Network | New | Research, forecasts, knowledge base |
| Coordination Engine | New | Matching, bulk purchasing, logistics |
| Unified Memory | OpenClaw + Hermes | Workspace + FTS5 + vector search |
| Learning Engine | Hermes | Self-improvement, skill creation |
| Gateway | OpenClaw | Telegram, API server |
| Tool Registry | MCP-compatible | Dynamic tool discovery |

## API

```bash
# Health check
curl https://superagent-zzgx.onrender.com/health

# Chat completion (OpenAI-compatible)
curl -X POST https://superagent-zzgx.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "superagent", "messages": [{"role": "user", "content": "Hello!"}]}'
```

## Telegram Bot

Send a message to `@superagent_bot` on Telegram.

## License

MIT
