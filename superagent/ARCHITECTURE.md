# SUPERAGENT — Unified Multi-Agent System Architecture

**Version:** 1.0.0  
**Date:** 2026-07-22  
**Status:** Buildable Architecture Specification  
**License:** MIT  

> A production-grade multi-agent system merging OpenClaw's gateway/orchestration  
> with Hermes Agent's self-improving learning loop, aligned with MCP, A2A, and  
> the emerging agent economy protocols.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Agent Hierarchy](#2-agent-hierarchy)
3. [Memory & Knowledge System](#3-memory--knowledge-system)
4. [Tool System](#4-tool-system)
5. [Messaging System](#5-messaging-system)
6. [Skill System](#6-skill-system)
7. [Kanban Task Board](#7-kanban-task-board)
8. [Deployment Plan](#8-deployment-plan)
9. [Technology Stack](#9-technology-stack)
10. [Directory Structure](#10-directory-structure)
11. [Configuration Schemas](#11-configuration-schemas)
12. [API Reference](#12-api-reference)
13. [Security Model](#13-security-model)
14. [Build Phases](#14-build-phases)

---

## 1. System Overview

### 1.1 What SUPERAGENT Is

SUPERAGENT is a **unified multi-agent operating system** that combines:

| Capability | Source | What It Does |
|-----------|--------|-------------|
| **Gateway** | OpenClaw | Multi-channel messaging (Telegram, Discord, WhatsApp, Signal, 20+ platforms) |
| **Agent Runtime** | OpenClaw | Session management, context assembly, model inference, tool execution |
| **Sub-agent Spawning** | OpenClaw | Non-blocking background agent tasks with push-based completion |
| **Memory System** | OpenClaw + Hermes | Layered memory: workspace files → session search → vector DB → knowledge graph |
| **Learning Loop** | Hermes | Autonomous skill creation, self-improvement, reflection cycles |
| **Skill System** | OpenClaw + Hermes | Markdown-based skills with progressive disclosure and self-evolution |
| **Kanban Board** | Hermes | Durable multi-agent task board with worker lanes and crash recovery |
| **Tool Gateway** | Hermes + OpenClaw | 70+ built-in tools + MCP protocol + Nous Tool Gateway |
| **API Server** | Hermes | OpenAI-compatible HTTP endpoint for programmatic access |
| **Cron/Scheduling** | OpenClaw | Exact-time cron + approximate heartbeat + event hooks |
| **Reflection** | Hermes | Post-task self-evaluation, memory consolidation, skill improvement |

### 1.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SUPERAGENT GATEWAY                           │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────────────┐ │
│  │   Channel    │ │   Agent      │ │   Control Plane             │ │
│  │   Adapters   │ │   Runtime    │ │   (WS API, HTTP API, Events)│ │
│  │  (20+ plats) │ │              │ │                             │ │
│  └──────────────┘ └──────────────┘ └─────────────────────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────────────┐ │
│  │   Cron       │ │   Heartbeat  │ │   Learning Engine           │ │
│  │   Scheduler  │ │   System     │ │   (Reflection + Improvement)│ │
│  └──────────────┘ └──────────────┘ └─────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│  👑 QUEEN    │  │  📋 KANBAN   │  │  🔌 TOOL GATEWAY │
│  Orchestrator│  │  Task Board  │  │  (MCP + Built-in │
│  (Router +   │  │  (Durable    │  │   + Nous Gateway)│
│   Planner)   │  │   Queue)     │  │                  │
└──────┬───────┘  └──────────────┘  └──────────────────┘
       │
  ┌────┼────┬────────┐
  ▼    ▼    ▼        ▼
┌────┐┌────┐┌────┐┌────────┐
│ SW1││ SW2││ SW3││ SW-N   │
│    ││    ││    ││        │
│ 💰 ││ 📊 ││ 🤝 ││ Custom │
└──┬─┘└──┬─┘└──┬─┘└───┬────┘
   │     │     │      │
   ▼     ▼     ▼      ▼
┌────────────────────────────────────────┐
│         WORKER AGENTS (Leaf)           │
│  Each with: tools, memory, skills      │
│  Spawned on-demand, model-overridable  │
└────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────────────────┐
│                    MEMORY & KNOWLEDGE LAYER                        │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐ │
│  │ Workspace  │ │ Session    │ │ Vector DB  │ │ Knowledge      │ │
│  │ Files      │ │ Search     │ │ (Semantic) │ │ Graph          │ │
│  │ (MD/AGENTS)│ │ (FTS5)     │ │            │ │ (Entities+Rels)│ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────────────────┐
│                    INTERFACE LAYER                                  │
│  Telegram │ Discord │ WhatsApp │ Signal │ WebChat │ API │ USSD    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.3 Key Design Principles

1. **OpenClaw as the skeleton, Hermes as the brain.** The Gateway, channel adapters, session management, and sub-agent spawning come from OpenClaw's battle-tested architecture. The learning loop, skill self-improvement, Kanban board, and reflection cycles come from Hermes.

2. **MCP-first tool integration.** Every external tool connection uses the Model Context Protocol. Built-in tools are wrapped as MCP servers internally. Third-party MCP servers plug in with zero code.

3. **A2A for inter-agent communication.** Agents discover each other via Agent Cards at `/.well-known/agent.json`. Task delegation uses the A2A task lifecycle (created → in-progress → completed/failed).

4. **Progressive memory disclosure.** Skills, knowledge, and context are loaded in tiers to minimize token cost. An agent with 200 skills pays roughly the same context cost as one with 40.

5. **Self-improvement as a first-class subsystem.** Every interaction is a potential training signal. The learning engine runs continuously, creating skills, updating memory, and refining prompts.

---

## 2. Agent Hierarchy

### 2.1 Three-Tier Agent Model

```
👑 QUEEN (Orchestrator)
├── Routes user intents to appropriate swarms
├── Manages cross-swarm coordination
├── Runs reflection cycles (daily)
├── Maintains user context and conversation state
└── Triggers self-improvement when patterns emerge

🐝 SWARM LEADERS (Domain Specialists)
├── Each owns a domain (market intel, coordination, etc.)
├── Decomposes complex tasks into worker assignments
├── Aggregates worker results into coherent responses
├── Manages worker spawning and lifecycle
└── Reports to Queen with structured results

🐜 WORKERS (Leaf Agents)
├── Execute specific tasks (data fetch, analysis, etc.)
├── Run with isolated context (no parent history)
├── Can use cheaper/faster models via override
├── Auto-terminated after task completion
└── Cannot spawn further workers (leaf constraint)
```

### 2.2 Agent Configuration

Each agent type is defined in the agent registry:

```yaml
# superagent/agents/registry.yaml
agents:
  queen:
    id: queen
    role: orchestrator
    model: anthropic/claude-sonnet-4-20250514
    workspace: ./workspace-queen
    can_spawn: true
    max_spawn_depth: 3
    subagent_model: openai/gpt-4o
    skills_allowlist: ["*"]  # all skills
    tools_allowlist: ["*"]   # all tools
    reflection_interval: 24h

  swarms:
    - id: market-intel
      role: swarm-leader
      model: openai/gpt-4o
      workspace: ./workspace-market-intel
      can_spawn: true
      max_spawn_depth: 2
      subagent_model: together/qwen3.5-9b  # cheap workers
      skills_allowlist: ["price-analysis", "demand-forecast", "market-research"]
      tools_allowlist: ["web_search", "web_fetch", "exec", "read", "write"]
      worker_lanes: ["data-collector", "analyst", "reporter"]

    - id: information-network
      role: swarm-leader
      model: openai/gpt-4o
      workspace: ./workspace-info-network
      can_spawn: true
      max_spawn_depth: 2
      subagent_model: together/qwen3.5-9b
      skills_allowlist: ["knowledge-base", "alert-system", "research"]
      tools_allowlist: ["web_search", "web_fetch", "exec", "read", "write", "mimo_web_search"]

    - id: coordination-engine
      role: swarm-leader
      model: openai/gpt-4o
      workspace: ./workspace-coordination
      can_spawn: true
      max_spawn_depth: 2
      subagent_model: together/qwen3.5-9b
      skills_allowlist: ["matching", "logistics", "bargaining", "resource-pooling"]
      tools_allowlist: ["web_search", "exec", "read", "write", "browser"]
```

### 2.3 Intent Routing (Queen)

The Queen classifies incoming messages and routes to swarms:

```python
# Conceptual routing logic (implemented as a skill)
INTENT_ROUTES = {
    "price_query":        ["market-intel"],
    "find_customer":      ["market-intel"],
    "compare_suppliers":  ["information-network"],
    "demand_forecast":    ["information-network"],
    "join_buying_group":  ["coordination-engine"],
    "find_transport":     ["coordination-engine"],
    "market_news":        ["information-network"],
    "list_product":       ["market-intel"],
    "general_chat":       [],  # Queen responds directly
}

# Multi-intent messages can route to multiple swarms
# Queen merges results into a single user-facing response
```

### 2.4 Sub-Agent Spawning (from OpenClaw)

Workers are spawned via `sessions_spawn`:

```typescript
// Queen spawns a worker through a swarm leader
sessions_spawn({
  task: "Research tomato prices across Nairobi markets today",
  model: "together/qwen3.5-9b",  // cheap model for data collection
  context: "isolated",            // fresh context, no parent history
  parentAgent: "market-intel",    // spawned under market-intel swarm
  timeout: 300,                   // 5 minute timeout
})
```

**Key properties:**
- Non-blocking: returns immediately with run ID
- Push-based: result announced back to requester
- Configurable nesting depth (Queen → Swarm → Worker = depth 2)
- Model override per spawn (workers use cheap models)
- Auto-termination after completion

### 2.5 A2A Agent Cards

Each agent exposes its capabilities via the A2A protocol:

```json
// /.well-known/agent.json (served by Gateway HTTP server)
{
  "name": "SUPERAGENT Queen",
  "description": "Central orchestrator for economic intelligence",
  "url": "https://superagent.example.com/a2a",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": true,
    "stateTransitionHistory": true
  },
  "skills": [
    {
      "id": "intent-routing",
      "name": "Intent Classification & Routing",
      "description": "Classifies user intent and routes to appropriate swarm"
    },
    {
      "id": "cross-swarm-merge",
      "name": "Cross-Swarm Result Merging",
      "description": "Combines results from multiple swarms into coherent response"
    }
  ],
  "defaultInputModes": ["text", "audio"],
  "defaultOutputModes": ["text", "audio"]
}
```

---

## 3. Memory & Knowledge System

### 3.1 Four-Layer Memory Architecture

SUPERAGENT merges OpenClaw's workspace-file memory with Hermes's four-layer system:

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: PROMPT MEMORY (Always-On Context)                      │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│ │ AGENTS.md   │ │ SOUL.md     │ │ USER.md     │ │ TOOLS.md  │ │
│ │ (Rules)     │ │ (Identity)  │ │ (Human)     │ │ (Env)     │ │
│ └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│ Frozen snapshot at session start. ~4K tokens max.               │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 2: SESSION MEMORY (Current Conversation)                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Active transcript in context window                         │ │
│ │ Auto-compaction on overflow with retry                      │ │
│ │ Session write locks prevent race conditions                 │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 3: EPISODIC MEMORY (Cross-Session Recall)                 │
│ ┌──────────────────────────┐ ┌──────────────────────────────┐  │
│ │ FTS5 Session Search      │ │ Vector DB (Semantic Search)  │  │
│ │ (Hermes keyword search)  │ │ (OpenClaw QMD + embeddings)  │  │
│ │ BM25 ranking             │ │ Cosine similarity            │  │
│ │ Bitemporal tracking      │ │ Cross-agent collections      │  │
│ └──────────────────────────┘ └──────────────────────────────┘  │
│ Hybrid retrieval: BM25 + dense vectors + re-ranking             │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 4: SEMANTIC MEMORY (Knowledge Graph + Skills)             │
│ ┌──────────────────────────┐ ┌──────────────────────────────┐  │
│ │ Knowledge Graph          │ │ Skill Library                │  │
│ │ (Entities + Relations)   │ │ (Procedural Memory)          │  │
│ │ Workers, Markets, Prices │ │ agentskills.io format        │  │
│ │ Temporal edges           │ │ Progressive disclosure       │  │
│ └──────────────────────────┘ └──────────────────────────────┘  │
│ Self-improving: new entities/skills created autonomously        │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Workspace Files (from OpenClaw)

These files are injected into every session as system prompt context:

| File | Purpose | Loaded | Max Size |
|------|---------|--------|----------|
| `AGENTS.md` | Agent personality, rules, protocols | Every session | 2,000 chars |
| `SOUL.md` | Identity, voice, values | Every session | 1,000 chars |
| `USER.md` | Human's preferences, context | Every session | 1,375 chars |
| `MEMORY.md` | Long-term curated memories | Main session only | 2,200 chars |
| `memory/YYYY-MM-DD.md` | Daily notes (raw logs) | On demand | Unlimited |
| `TOOLS.md` | Local environment notes | Every session | 500 chars |
| `HEARTBEAT.md` | Periodic check checklist | Heartbeat turns | 500 chars |

**Hermes enhancement:** These files are frozen snapshots at session start. The learning engine updates them *between* sessions, never mid-conversation. This preserves LLM prefix cache.

### 3.3 Session Search (FTS5 from Hermes)

Every session is stored in SQLite with FTS5 full-text indexing:

```sql
-- Session storage schema
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    peer_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id),
    role TEXT NOT NULL,  -- 'user', 'assistant', 'system', 'tool'
    content TEXT NOT NULL,
    tool_calls TEXT,     -- JSON array of tool call objects
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FTS5 index for full-text search
CREATE VIRTUAL TABLE messages_fts USING fts5(
    content,
    session_id,
    role,
    content=messages,
    content_rowid=id,
    tokenize='porter unicode61'
);

-- Triggers to keep FTS index in sync
CREATE TRIGGER messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content, session_id, role)
    VALUES (new.id, new.content, new.session_id, new.role);
END;
```

**Search tool available to agents:**

```typescript
// session_search tool
{
  name: "session_search",
  description: "Search past conversations for relevant context",
  parameters: {
    query: string,           // search query
    agent_id?: string,       // limit to specific agent
    limit?: number,          // default 10
    after?: string,          // ISO date filter
    before?: string          // ISO date filter
  }
}
```

### 3.4 Vector Database (Semantic Memory)

For semantic search beyond keyword matching:

```yaml
# Vector store configuration
vector_store:
  provider: qdrant          # or chromadb, pgvector
  url: http://localhost:6333
  collections:
    - name: agent_memory
      dimensions: 1536       # text-embedding-3-small
      distance: cosine
    - name: market_knowledge
      dimensions: 1536
      distance: cosine
  embedding:
    provider: openai
    model: text-embedding-3-small
    batch_size: 100
```

**Hybrid retrieval pattern:**

```python
async def hybrid_search(query: str, limit: int = 10) -> list[Result]:
    """Combine FTS5 keyword search with vector similarity search."""
    # 1. BM25 keyword search
    fts_results = db.execute(
        "SELECT *, rank FROM messages_fts WHERE messages_fts MATCH ? ORDER BY rank LIMIT ?",
        (query, limit * 2)
    ).fetchall()

    # 2. Vector similarity search
    embedding = await embed(query)
    vec_results = await qdrant.search(
        collection="agent_memory",
        query_vector=embedding,
        limit=limit * 2
    )

    # 3. Merge and re-rank
    merged = merge_results(fts_results, vec_results)
    reranked = await reranker.rerank(query, merged, top_n=limit)
    return reranked
```

### 3.5 Knowledge Graph (Semantic Memory)

Entities and relationships extracted from interactions:

```yaml
# Knowledge graph schema
knowledge_graph:
  backend: falkordb          # Redis-based, ultra-low latency
  url: redis://localhost:6379

  node_types:
    - Worker: { properties: [id, name, location, products, trust_score] }
    - Market: { properties: [id, name, location, operating_hours, type] }
    - Product: { properties: [id, name, category, unit] }
    - Supplier: { properties: [id, name, location, products] }
    - Price: { properties: [amount, currency, unit, timestamp] }
    - Event: { properties: [type, description, impact, timestamp] }

  edge_types:
    - (Worker)-[:SELLS]->(Product)
    - (Worker)-[:LOCATED_AT]->(Market)
    - (Product)-[:PRICED_AT]->(Price)
    - (Price)-[:AT_MARKET]->(Market)
    - (Supplier)-[:SUPPLIES]->(Product)
    - (Event)-[:AFFECTS]->(Market)
    - (Event)-[:AFFECTS]->(Product)
    - (Worker)-[:COLLABORATES_WITH]->(Worker)
```

**Knowledge extraction pipeline (Hermes learning loop):**

```
Session interaction
    → LLM extracts entities and relationships
    → Conflict detection against existing graph
    → Merge/update/create nodes and edges
    → Log extraction for audit trail
```

### 3.6 Memory Consolidation (Hermes Learning Loop)

The learning engine runs periodic memory consolidation:

```yaml
# Memory consolidation config
learning:
  consolidation:
    interval: 24h           # Run daily
    batch_size: 50          # Process 50 sessions at a time
    steps:
      - extract_entities: true
      - extract_relationships: true
      - detect_conflicts: true
      - update_memory_files: true   # Update MEMORY.md, USER.md
      - create_skills: true         # Auto-create skills from patterns
      - update_knowledge_graph: true

  reflection:
    trigger: post_task       # After each completed task
    evaluate:
      - task_completion: true
      - accuracy: true
      - efficiency: true
      - user_satisfaction: true
    actions:
      - update_skill: true
      - save_memory: true
      - adjust_routing: true
```

---

## 4. Tool System

### 4.1 Unified Tool Architecture

SUPERAGENT merges three tool sources:

```
┌─────────────────────────────────────────────────────────────┐
│                    TOOL REGISTRY                             │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│  │  Built-in Tools   │  │  MCP Servers      │  │  Nous     │ │
│  │  (OpenClaw core)  │  │  (Protocol std)   │  │  Gateway  │ │
│  │                   │  │                   │  │           │ │
│  │  exec, read, write│  │  GitHub, Postgres │  │  Web search│ │
│  │  web_fetch, browse│  │  Slack, Drive     │  │  Image gen │ │
│  │  sessions_spawn   │  │  Custom servers   │  │  TTS      │ │
│  │  cron, message    │  │                   │  │  Browser  │ │
│  └──────────────────┘  └──────────────────┘  └───────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  Tool Policy Pipeline                                     ││
│  │  Profile → allow/deny → Provider → Sandbox → Channel     ││
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Built-in Tools (from OpenClaw)

| Category | Tools | Purpose |
|----------|-------|---------|
| **Runtime** | `exec`, `process` | Run shell commands, manage processes |
| **Files** | `read`, `write`, `edit` | Workspace file operations |
| **Web** | `web_search`, `web_fetch` | Search and fetch web content |
| **Browser** | `browser` | Full browser automation |
| **Messaging** | `message` | Send replies to channels |
| **Sessions** | `sessions_spawn`, `sessions_yield` | Agent orchestration |
| **Automation** | `cron`, `heartbeat_respond` | Scheduled work |
| **Gateway** | `gateway`, `nodes` | Infrastructure control |
| **Search** | `session_search`, `memory_search` | Memory retrieval |

### 4.3 MCP Integration (Protocol Standard)

SUPERAGENT acts as an MCP client, connecting to external MCP servers:

```yaml
# MCP server configuration
mcp:
  servers:
    - name: github
      command: npx
      args: ["-y", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_TOKEN: ${GITHUB_TOKEN}

    - name: postgres
      command: npx
      args: ["-y", "@modelcontextprotocol/server-postgres"]
      env:
        DATABASE_URL: ${DATABASE_URL}

    - name: filesystem
      command: npx
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/data"]

    - name: browser
      command: npx
      args: ["-y", "@anthropic/server-puppeteer"]

  # Dynamic MCP server discovery (from nodes)
  node_servers:
    enabled: true
    auto_discover: true
```

**MCP client implementation:**

```python
# mcp_client.py — MCP server connection manager
import json
import asyncio
from typing import Any

class MCPClient:
    """Manages connections to MCP servers."""

    def __init__(self):
        self.servers: dict[str, MCPServerConnection] = {}

    async def connect(self, config: dict) -> None:
        """Start an MCP server process and connect via stdio."""
        proc = await asyncio.create_subprocess_exec(
            config["command"], *config.get("args", []),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            env={**os.environ, **config.get("env", {})}
        )
        conn = MCPServerConnection(proc, config["name"])
        await conn.initialize()
        self.servers[config["name"]] = conn

    async def list_tools(self) -> list[dict]:
        """Aggregate tools from all connected MCP servers."""
        all_tools = []
        for name, conn in self.servers.items():
            tools = await conn.request("tools/list", {})
            for tool in tools.get("tools", []):
                tool["_server"] = name
                all_tools.append(tool)
        return all_tools

    async def call_tool(self, server: str, name: str, arguments: dict) -> Any:
        """Call a tool on a specific MCP server."""
        conn = self.servers[server]
        return await conn.request("tools/call", {
            "name": name,
            "arguments": arguments
        })
```

### 4.4 Nous Tool Gateway (from Hermes)

The Nous Tool Gateway provides cloud-hosted tool infrastructure:

```yaml
# Nous Tool Gateway configuration
nous_gateway:
  enabled: true
  api_key: ${NOUS_GATEWAY_KEY}
  base_url: https://gateway.nousresearch.com/v1

  tools:
    web_search:
      enabled: true
      provider: firecrawl
    image_generation:
      enabled: true
      models: ["flux-2", "gpt-image", "ideogram-v3"]
    tts:
      enabled: true
      provider: openai
    cloud_browser:
      enabled: true
      provider: browser-use
```

### 4.5 Tool Policy Pipeline

Every tool call passes through a multi-layer filter before execution:

```
1. Profile Check     → Is tool in active profile (minimal/coding/full)?
2. Allow/Deny List   → Per-agent allowlist overrides global defaults
3. Provider Check    → Does the model provider support this tool type?
4. Sandbox Rules     → Workspace isolation, network restrictions
5. Channel Perms     → Does the channel allow this tool?
6. Exec Approvals    → Fine-grained shell command control
7. Execute           → Tool runs, result sanitized and returned
```

```yaml
# Tool policy configuration
tool_policy:
  profiles:
    minimal:
      allowed: ["read", "write", "web_search", "session_search"]
    coding:
      allowed: ["read", "write", "edit", "exec", "process", "web_search"]
    full:
      allowed: ["*"]

  per_agent:
    queen:
      profile: full
      exec_approval: false  # Queen can exec freely
    market-intel:
      profile: coding
      exec_approval: true   # Workers need approval for exec
    worker:
      profile: minimal
      exec_approval: true

  exec_rules:
    - pattern: "rm -rf *"
      action: deny
    - pattern: "sudo *"
      action: require_approval
    - pattern: "pip install *"
      action: allow
```

### 4.6 Dynamic Tool Discovery (Code Mode)

For agents with large tool catalogs, SUPERAGENT uses progressive disclosure:

```
Level 0: tool_list() → [{name, description}]      (~2K tokens)
Level 1: tool_describe(name) → Full schema          (~500 tokens each)
Level 2: tool_search(query) → Relevant tools only   (~1K tokens)
```

This keeps context costs low even with 100+ available tools.

---

## 5. Messaging System

### 5.1 Unified Gateway (from OpenClaw)

One Gateway process serves all messaging channels:

```
┌──────────────────────────────────────────────────────────────┐
│                    SUPERAGENT GATEWAY                         │
│                                                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │Telegram │ │Discord  │ │WhatsApp │ │Signal   │          │
│  │(grammY) │ │(d.js)   │ │(Baileys)│ │(signal- │          │
│  │         │ │         │ │         │ │protocol)│          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │Slack    │ │Matrix   │ │QQ Bot   │ │WebChat  │          │
│  │         │ │         │ │         │ │(WS API) │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │DingTalk │ │Feishu   │ │iMessage │ │API      │          │
│  │         │ │         │ │         │ │(HTTP)   │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│                                                              │
│  WebSocket Server (127.0.0.1:18789)                         │
│  HTTP API Server (0.0.0.0:18790)                            │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Channel Configuration

```yaml
# Channel configuration
channels:
  telegram:
    enabled: true
    token: ${TELEGRAM_BOT_TOKEN}
    mode: webhook
    webhook_url: https://superagent.example.com/telegram/webhook
    features:
      group_chat: true
      mention_pattern: "@superagent"
      media_support: true
      voice_transcription: true

  discord:
    enabled: true
    token: ${DISCORD_BOT_TOKEN}
    features:
      slash_commands: true
      threads: true
      reactions: true

  whatsapp:
    enabled: true
    provider: baileys   # unofficial, or meta_cloud for official
    features:
      group_chat: true
      voice_notes: true
      media_support: true

  api:
    enabled: true
    port: 18790
    cors: ["https://dashboard.superagent.example.com"]
    auth:
      type: bearer
      token: ${API_TOKEN}
```

### 5.3 Message Flow

```
User sends message
    │
    ▼
Channel Adapter receives
    │
    ▼
Access Control (allowlists, DM pairing)
    │
    ▼
Session Resolution (deterministic routing)
    │
    ▼
Agent Resolution (binding rules: peer → guild → channel → default)
    │
    ▼
Queen Orchestrator
    │
    ├─ Intent classification
    ├─ Swarm routing
    ├─ Worker spawning
    │
    ▼
Response Assembly
    │
    ▼
Channel Adapter sends reply
    │
    ▼
User receives response
```

### 5.4 Binding Rules

Bindings map inbound messages to agents:

```yaml
# Binding configuration
bindings:
  # Specific user → specific agent
  - match:
      channel: telegram
      peer: "user:123456789"
    agent: queen

  # Telegram group → market-intel swarm
  - match:
      channel: telegram
      peer: "group:market-nairobi"
    agent: market-intel

  # Discord server + role → coordination engine
  - match:
      channel: discord
      guild: "guild:111111111"
      roles: ["coordinator"]
    agent: coordination-engine

  # Default → queen
  - match: {}
    agent: queen
```

### 5.5 Hermes Platform Parity

Hermes brings additional platform adapters that merge into the Gateway:

| Platform | Source | Notes |
|----------|--------|-------|
| Telegram | Both | OpenClaw (grammY) primary, Hermes features merged |
| Discord | Both | OpenClaw (d.js) primary |
| WhatsApp | Both | Baileys unofficial, Meta Cloud optional |
| Signal | OpenClaw | signal-protocol |
| Slack | Both | |
| DingTalk | Hermes | Chinese workplace platform |
| Feishu | OpenClaw | Chinese workplace platform |
| WeCom | Hermes | WeChat Work |
| Weixin | Hermes | WeChat |
| QQ Bot | OpenClaw | Chinese messaging |
| Email | Hermes | SMTP/IMAP adapter |
| SMS | Hermes | Via Africa's Talking / Twilio |
| API Server | Hermes | OpenAI-compatible HTTP endpoint |
| WebChat | OpenClaw | Browser-based chat via WS API |

---

## 6. Skill System

### 6.1 Unified Skill Format (agentskills.io)

Skills follow the open standard, compatible with both OpenClaw and Hermes:

```markdown
---
name: price-analysis
version: 1.2.0
description: Analyze commodity prices across markets
category: market-intelligence
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["DATABASE_URL"]
  hermes:
    requires_toolsets: ["terminal", "web"]
    fallback_for_toolsets: []
---

## When to Use

Activate when the user asks about:
- Current prices for any commodity
- Price comparisons across markets
- Price trends over time
- Fair pricing recommendations

## Instructions

1. Query the price database for the requested commodity
2. If no local data, search government sources via web_fetch
3. Present prices in a table format with market, price, unit, date
4. Calculate 7-day moving average if trend data available
5. Flag significant price changes (>10% in 7 days) with alerts

## Price Data Sources

- Primary: Crowdsourced reports from users
- Secondary: Kenya National Bureau of Statistics
- Tertiary: Web search for recent price news

## Output Format

💰 **{Commodity} Prices** — {Date}

| Market | Price | Unit | Change (7d) |
|--------|-------|------|-------------|
| {market} | KSh {price} | {unit} | {change}% |

💡 **Insight:** {one-line actionable recommendation}
```

### 6.2 Skill Loading Precedence

| Priority | Source | Path |
|----------|--------|------|
| 1 (highest) | Workspace skills | `<workspace>/skills/` |
| 2 | Project agent skills | `<workspace>/.agents/skills/` |
| 3 | Personal agent skills | `~/.agents/skills/` |
| 4 | Managed/local skills | `~/.superagent/skills/` |
| 5 | Bundled skills | Shipped with install |
| 6 (lowest) | Plugin skills | Installed plugins |

### 6.3 Progressive Disclosure (from Hermes)

Skills are loaded in tiers to minimize token cost:

```
Level 0: skills_list()
  → Returns: [{name, description, category}] for ALL skills
  → Cost: ~3K tokens for 200 skills
  → Loaded: Every session

Level 1: skill_view(name)
  → Returns: Full SKILL.md content
  → Cost: ~1-3K tokens per skill
  → Loaded: When skill is activated

Level 2: skill_view(name, path)
  → Returns: Specific reference file within skill
  → Cost: Variable
  → Loaded: On demand
```

### 6.4 Autonomous Skill Creation (from Hermes)

The learning engine creates skills from experience. **Triggers:**

```yaml
skill_creation:
  triggers:
    min_tool_calls: 5           # 5+ tool calls in workflow
    error_recovery: true        # Recovered from an error
    user_correction: true       # User corrected the agent
    novel_workflow: true        # Non-obvious workflow that succeeded

  process:
    1. detect_trigger: "Did this interaction warrant a skill?"
    2. extract_pattern: "What was the generalizable procedure?"
    3. write_skill: "Create SKILL.md in agentskills.io format"
    4. validate: "Test skill against original interaction"
    5. register: "Add to skill library with metadata"

  storage: ~/.superagent/skills/auto-created/
```

### 6.5 Skill Self-Improvement (from Hermes)

Skills evolve through use:

```yaml
skill_improvement:
  triggers:
    better_path_found: true     # Agent finds a more efficient approach
    user_feedback: true         # User suggests improvement
    failure_analysis: true      # Skill failed, needs fix

  actions:
    - name: patch
      description: "Targeted string replacement (preferred)"
      example:
        old: "Query SQLite database directly"
        new: "Use hybrid search (FTS5 + vector) for better results"

    - name: edit
      description: "Rewrite specific section"

    - name: write_file
      description: "Add reference file to skill"

  versioning:
    strategy: semantic           # major.minor.patch
    auto_increment: patch        # Auto-increment patch on changes
```

### 6.6 Skill Workshop (from OpenClaw)

Human-in-the-loop governance for skill changes:

```yaml
skill_workshop:
  enabled: true
  mode: proposal_queue          # agent proposes, human approves
  auto_approve:
    threshold: 0.95             # Auto-approve if confidence > 95%
    categories: ["bug_fix", "minor_edit"]
  notification:
    channel: telegram
    target: "user:admin"
```

### 6.7 `/learn` Command (from Hermes)

Turn reference material into reusable skills:

```
User: /learn https://docs.safaricom.co.ke/api/daraja
Agent: [Fetches documentation, creates skill]

User: /learn ./my-analysis-script.py
Agent: [Reads script, creates skill with instructions]

User: /learn The workflow I just did for market analysis
Agent: [Reviews session, extracts pattern into skill]
```

---

## 7. Kanban Task Board

### 7.1 Overview (from Hermes)

The Kanban board is a durable multi-agent task queue backed by SQLite:

```
┌──────────────────────────────────────────────────────────────┐
│                    KANBAN BOARD                               │
│                                                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────┐ │
│  │ TRIAGE  │ │  TODO   │ │ RUNNING │ │ BLOCKED │ │ DONE │ │
│  │         │ │         │ │         │ │         │ │      │ │
│  │ [task1] │ │ [task3] │ │ [task5] │ │ [task7] │ │[t2]  │ │
│  │ [task2] │ │ [task4] │ │ [task6] │ │         │ │[t8]  │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────┘ │
│                                                              │
│  Worker Lanes:                                               │
│  ├── researcher: [task3, task5]                              │
│  ├── analyst: [task4, task6]                                 │
│  └── reporter: [task7]                                       │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 Task State Machine

```
triage → todo → ready → running → done → archived
                    ↑        │
                    └────────┘ (retry)
                    │
                 blocked → unblock → ready
```

### 7.3 Database Schema

```sql
-- Kanban database (separate from session store)
CREATE TABLE boards (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    board_id TEXT REFERENCES boards(id),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'triage',  -- triage, todo, ready, running, blocked, done, archived
    lane TEXT,                      -- worker lane (researcher, analyst, reporter)
    assigned_to TEXT,               -- agent profile id
    priority INTEGER DEFAULT 3,    -- 1 (highest) to 5 (lowest)
    parent_id TEXT REFERENCES tasks(id),  -- parent task for subtasks
    workspace_dir TEXT,             -- scratch directory for task work
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE task_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT REFERENCES tasks(id),
    author TEXT NOT NULL,           -- agent id or 'human'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE task_links (
    source_id TEXT REFERENCES tasks(id),
    target_id TEXT REFERENCES tasks(id),
    relation TEXT DEFAULT 'depends_on',  -- depends_on, blocks, related
    PRIMARY KEY (source_id, target_id)
);
```

### 7.4 Dispatcher Loop

A long-lived loop that assigns tasks to workers:

```python
# Dispatcher runs every 60 seconds
async def dispatch_loop():
    while True:
        # 1. Find ready tasks in each lane
        for lane in get_lanes():
            ready_tasks = db.query(
                "SELECT * FROM tasks WHERE status='ready' AND lane=? ORDER BY priority",
                (lane,)
            )

            # 2. Find available worker for lane
            for task in ready_tasks:
                worker = find_available_worker(lane)
                if worker:
                    # 3. Assign and run
                    db.execute(
                        "UPDATE tasks SET status='running', assigned_to=?, started_at=? WHERE id=?",
                        (worker.id, datetime.now(), task.id)
                    )
                    # 4. Spawn worker agent
                    await sessions_spawn({
                        task: task.description,
                        model: worker.model,
                        context: "isolated",
                        workspace: task.workspace_dir,
                        on_complete: lambda result: complete_task(task.id, result)
                    })

        # 5. Check for completed/failed tasks
        # 6. Handle blocked tasks (human-in-the-loop)
        # 7. Reclaim crashed tasks (no heartbeat for >5min)
        await asyncio.sleep(60)
```

### 7.5 Human-in-the-Loop

Tasks can be blocked waiting for human input:

```
Worker: Task requires human decision. Should we use Supplier A or Supplier B?
         [Supplier A: KSh 80/kg, delivery 2 days]
         [Supplier B: KSh 75/kg, delivery 5 days]

Human: [Clicks "Supplier A"]

Worker: Resuming task with Supplier A...
```

---

## 8. Deployment Plan

### 8.1 Docker Architecture

```yaml
# docker-compose.yml
version: "3.9"

services:
  # Main Gateway process
  gateway:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "18789:18789"   # WebSocket API
      - "18790:18790"   # HTTP API
    volumes:
      - gateway-data:/root/.superagent
      - ./workspace:/root/.superagent/workspace
    environment:
      - SUPERAGENT_CONFIG=/root/.superagent/superagent.json
    depends_on:
      - postgres
      - redis
      - qdrant
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:18790/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # PostgreSQL (session store + Kanban + structured data)
  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: superagent
      POSTGRES_USER: superagent
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    restart: unless-stopped

  # Redis (caching, pub/sub, Kanban coordination)
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped

  # Qdrant (vector database for semantic memory)
  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant-data:/qdrant/storage
    ports:
      - "6333:6333"
    restart: unless-stopped

  # FalkorDB (knowledge graph, Redis-compatible)
  falkordb:
    image: falkordb/falkordb:latest
    volumes:
      - falkordb-data:/data
    ports:
      - "6380:6379"
    restart: unless-stopped

  # MCP servers (optional, can also run on nodes)
  mcp-github:
    image: node:22-alpine
    command: npx -y @modelcontextprotocol/server-github
    environment:
      GITHUB_PERSONAL_ACCESS_TOKEN: ${GITHUB_TOKEN}
    profiles:
      - mcp

volumes:
  gateway-data:
  postgres-data:
  redis-data:
  qdrant-data:
  falkordb-data:
```

### 8.2 Dockerfile

```dockerfile
# Dockerfile
FROM node:22-slim AS base

# Install Python (for Hermes agent runtime)
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    curl git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Install Node.js dependencies (for OpenClaw gateway)
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --production

# Copy application code
COPY . .

# Create workspace directory
RUN mkdir -p /root/.superagent/workspace

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:18790/health || exit 1

# Start gateway
CMD ["node", "dist/gateway.js"]
```

### 8.3 Hosting Options

| Phase | Platform | Config | Monthly Cost |
|-------|----------|--------|-------------|
| **MVP** | Fly.io (Johannesburg) | 1 shared-cpu-2x (1GB), Postgres, Redis | $15-25 |
| **Beta** | Fly.io + managed DBs | 2 shared-cpu-2x, Supabase, Upstash | $30-50 |
| **Growth** | Railway or dedicated VPS | 4GB RAM, dedicated Postgres, Redis | $80-150 |
| **Scale** | Kubernetes (GKE/EKS) | Multi-node, managed databases | $300-800 |

### 8.4 Cost Breakdown (MVP)

| Component | Service | Cost/mo |
|-----------|---------|---------|
| Gateway hosting | Fly.io (Johannesburg, 1 shared VM) | $7 |
| PostgreSQL | Supabase free tier | $0 |
| Redis | Upstash free tier | $0 |
| Vector DB | Qdrant self-hosted (in Docker) | $0 |
| Knowledge graph | FalkorDB self-hosted (in Docker) | $0 |
| LLM API | OpenRouter (Qwen3.5 9B for workers) | $5-15 |
| LLM API | OpenRouter (GPT-4o for Queen) | $5-10 |
| Monitoring | Helicone free tier | $0 |
| Domain + DNS | Cloudflare | $0 |
| Telegram | Free | $0 |
| **Total MVP** | | **$17-32/mo** |

### 8.5 Scaling Path

```
100 users    → $17-32/mo  → Single Docker Compose on Fly.io
1K users     → $50-80/mo  → Dedicated VPS, managed Postgres
10K users    → $150-300/mo → Multiple Gateway instances, Redis cluster
100K users   → $500-1K/mo  → Kubernetes, dedicated GPU for self-hosted LLM
```

---

## 9. Technology Stack

### 9.1 Core Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Runtime** | Node.js | 22.x | Gateway process |
| **Runtime** | Python | 3.12 | Agent runtime, tools, learning engine |
| **Gateway** | OpenClaw core | latest | Multi-channel messaging, session management |
| **Agent Framework** | Custom (merge OpenClaw + Hermes) | 1.0 | Agent loop, tool dispatch, memory |
| **Database** | PostgreSQL | 16 | Session store, Kanban, structured data |
| **Cache** | Redis | 7 | Caching, pub/sub, rate limiting |
| **Vector DB** | Qdrant | latest | Semantic memory, embeddings |
| **Knowledge Graph** | FalkorDB | latest | Entity relationships, graph queries |
| **Full-Text Search** | SQLite FTS5 | built-in | Session search (embedded in agent) |
| **Embeddings** | OpenAI text-embedding-3-small | - | Vector embeddings |
| **MCP Client** | @modelcontextprotocol/sdk | latest | Tool protocol standard |
| **Container** | Docker + Docker Compose | latest | Deployment |

### 9.2 LLM Providers

| Provider | Models | Use Case | Cost (per 1M tokens) |
|----------|--------|----------|---------------------|
| **OpenAI** | GPT-4o, GPT-5.2 | Queen reasoning, complex analysis | $2.50 / $10.00 |
| **Anthropic** | Claude Sonnet 4 | Queen alternative, code tasks | $3.00 / $15.00 |
| **OpenRouter** | Meta-routing | Single API, model flexibility | Varies |
| **Together AI** | Qwen3.5 9B, Gemma 4 31B | Worker agents (cheap) | $0.17 / $0.25 |
| **Together AI** | DeepSeek V4 Pro | Complex reasoning tasks | $1.74 / $3.48 |
| **Ollama** | Llama 3.2 1B, Phi-4 Mini | Edge/offline inference | Free (self-hosted) |

### 9.3 Python Dependencies

```txt
# requirements.txt
# Agent runtime
openai>=1.50.0
anthropic>=0.34.0
httpx>=0.27.0

# Database
psycopg2-binary>=2.9.9
redis>=5.0.0
sqlite3-to-csv>=0.1.0  # built-in sqlite3

# Vector store
qdrant-client>=1.12.0

# Knowledge graph
falkordb>=1.0.0

# Embeddings
openai>=1.50.0  # for embedding API

# MCP
mcp>=1.0.0

# Tools
beautifulsoup4>=4.12.0
playwright>=1.47.0

# Structured output
instructor>=1.6.0
pydantic>=2.9.0

# Learning engine
numpy>=1.26.0
scikit-learn>=1.5.0

# Monitoring
prometheus-client>=0.21.0
```

### 9.4 Node.js Dependencies

```json
{
  "dependencies": {
    "openclaw": "latest",
    "@modelcontextprotocol/sdk": "^1.0.0",
    "grammy": "^1.25.0",
    "discord.js": "^14.16.0",
    "baileys": "^6.7.0",
    "better-sqlite3": "^11.0.0",
    "ws": "^8.18.0",
    "express": "^4.21.0",
    "zod": "^3.23.0",
    "pino": "^9.4.0"
  }
}
```

---

## 10. Directory Structure

```
superagent/
├── ARCHITECTURE.md              # This document
├── docker-compose.yml           # Production deployment
├── Dockerfile                   # Container build
├── package.json                 # Node.js dependencies
├── requirements.txt             # Python dependencies
├── tsconfig.json                # TypeScript config
│
├── src/                         # Source code
│   ├── gateway/                 # OpenClaw-derived gateway
│   │   ├── index.ts             # Gateway entry point
│   │   ├── channels/            # Channel adapters
│   │   │   ├── telegram.ts
│   │   │   ├── discord.ts
│   │   │   ├── whatsapp.ts
│   │   │   ├── signal.ts
│   │   │   ├── slack.ts
│   │   │   └── api.ts           # HTTP API adapter
│   │   ├── sessions/            # Session management
│   │   │   ├── store.ts         # Session persistence
│   │   │   ├── resolver.ts      # Session key resolution
│   │   │   └── compaction.ts    # Context compaction
│   │   ├── router/              # Message routing
│   │   │   ├── bindings.ts      # Binding rules
│   │   │   └── intent.ts        # Intent classification
│   │   └── cron/                # Scheduler
│   │       ├── scheduler.ts
│   │       └── heartbeat.ts
│   │
│   ├── agent/                   # Agent runtime (merge)
│   │   ├── runtime.ts           # Core agent loop
│   │   ├── queen.ts             # Queen orchestrator
│   │   ├── swarm.ts             # Swarm leader base class
│   │   ├── worker.ts            # Worker agent base class
│   │   ├── context.ts           # Context assembly
│   │   └── model.ts             # Model provider abstraction
│   │
│   ├── memory/                  # Memory system (merge)
│   │   ├── workspace.ts         # Workspace file management
│   │   ├── session-search.ts    # FTS5 session search
│   │   ├── vector-store.ts      # Vector DB integration
│   │   ├── knowledge-graph.ts   # Graph DB integration
│   │   ├── hybrid-search.ts     # BM25 + vector + rerank
│   │   └── consolidation.ts     # Memory consolidation engine
│   │
│   ├── tools/                   # Tool system (merge)
│   │   ├── registry.ts          # Central tool registry
│   │   ├── builtin/             # Built-in tools
│   │   │   ├── exec.ts
│   │   │   ├── read.ts
│   │   │   ├── write.ts
│   │   │   ├── web_search.ts
│   │   │   ├── web_fetch.ts
│   │   │   ├── browser.ts
│   │   │   ├── session_search.ts
│   │   │   └── mimo_web_search.ts
│   │   ├── mcp/                 # MCP client
│   │   │   ├── client.ts
│   │   │   └── manager.ts
│   │   └── policy.ts            # Tool policy pipeline
│   │
│   ├── skills/                  # Skill system (merge)
│   │   ├── loader.ts            # Skill file loader
│   │   ├── registry.ts          # Skill registry
│   │   ├── disclosure.ts        # Progressive disclosure
│   │   ├── workshop.ts          # Skill workshop (human-in-loop)
│   │   └── auto-create.ts       # Autonomous skill creation
│   │
│   ├── kanban/                  # Kanban task board (Hermes)
│   │   ├── board.ts             # Board management
│   │   ├── task.ts              # Task state machine
│   │   ├── dispatcher.ts        # Worker dispatch loop
│   │   └── worker-lanes.ts      # Lane management
│   │
│   ├── learning/                # Learning engine (Hermes)
│   │   ├── reflection.ts        # Post-task reflection
│   │   ├── skill-evolution.ts   # Skill self-improvement
│   │   ├── memory-nudge.ts      # Periodic memory curation
│   │   └── trajectory.ts        # Trajectory logging
│   │
│   ├── api/                     # HTTP API server (Hermes)
│   │   ├── server.ts            # Express/Fastify server
│   │   ├── routes/
│   │   │   ├── chat.ts          # /v1/chat/completions
│   │   │   ├── responses.ts     # /v1/responses
│   │   │   ├── runs.ts          # /v1/runs
│   │   │   ├── models.ts        # /v1/models
│   │   │   ├── capabilities.ts  # /v1/capabilities
│   │   │   └── health.ts        # /health
│   │   └── a2a/                 # A2A protocol endpoints
│   │       ├── agent-card.ts    # /.well-known/agent.json
│   │       └── tasks.ts         # A2A task lifecycle
│   │
│   └── config/                  # Configuration
│       ├── schema.ts            # Config schema (Zod)
│       ├── loader.ts            # Config file loader
│       └── defaults.ts          # Default values
│
├── workspace/                   # Default agent workspace
│   ├── AGENTS.md                # Agent personality
│   ├── SOUL.md                  # Identity
│   ├── USER.md                  # Human context
│   ├── MEMORY.md                # Long-term memory
│   ├── TOOLS.md                 # Environment notes
│   ├── HEARTBEAT.md             # Heartbeat checklist
│   ├── memory/                  # Daily notes
│   │   └── YYYY-MM-DD.md
│   └── skills/                  # Workspace skills
│       └── custom/
│
├── skills/                      # Managed skills (bundled)
│   ├── price-analysis/
│   │   └── SKILL.md
│   ├── demand-forecast/
│   │   └── SKILL.md
│   ├── market-research/
│   │   └── SKILL.md
│   ├── matching/
│   │   └── SKILL.md
│   ├── logistics/
│   │   └── SKILL.md
│   └── ... (20+ bundled skills)
│
├── migrations/                  # Database migrations
│   ├── 001_sessions.sql
│   ├── 002_kanban.sql
│   ├── 003_knowledge_graph.sql
│   └── 004_fts5_indexes.sql
│
├── tests/                       # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── scripts/                     # Utility scripts
    ├── setup.sh                 # Initial setup
    ├── migrate.sh               # Run migrations
    └── seed.sh                  # Seed data
```

---

## 11. Configuration Schemas

### 11.1 Main Configuration File

```jsonc
// superagent.json — Main configuration
{
  "$schema": "./src/config/schema.json",
  "version": "1.0.0",

  // Gateway settings
  "gateway": {
    "host": "0.0.0.0",
    "wsPort": 18789,
    "httpPort": 18790,
    "auth": {
      "token": "${GATEWAY_AUTH_TOKEN}"
    },
    "tls": {
      "enabled": false,
      "cert": "./certs/cert.pem",
      "key": "./certs/key.pem"
    }
  },

  // Agent configuration
  "agents": {
    "defaults": {
      "model": "openai/gpt-4o",
      "temperature": 0.7,
      "maxTokens": 4096,
      "subagents": {
        "model": "together/qwen3.5-9b",
        "runTimeoutSeconds": 300,
        "maxConcurrent": 10
      }
    },
    "list": [
      {
        "id": "queen",
        "workspace": "./workspace",
        "model": "anthropic/claude-sonnet-4-20250514",
        "role": "orchestrator",
        "canSpawn": true,
        "maxSpawnDepth": 3
      },
      {
        "id": "market-intel",
        "workspace": "./workspace-market-intel",
        "model": "openai/gpt-4o",
        "role": "swarm-leader",
        "canSpawn": true,
        "maxSpawnDepth": 2,
        "subagents": {
          "model": "together/qwen3.5-9b"
        }
      },
      {
        "id": "info-network",
        "workspace": "./workspace-info-network",
        "model": "openai/gpt-4o",
        "role": "swarm-leader",
        "canSpawn": true,
        "maxSpawnDepth": 2
      },
      {
        "id": "coordination",
        "workspace": "./workspace-coordination",
        "model": "openai/gpt-4o",
        "role": "swarm-leader",
        "canSpawn": true,
        "maxSpawnDepth": 2
      }
    ]
  },

  // Channel configuration
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "${TELEGRAM_BOT_TOKEN}",
      "mode": "webhook",
      "webhookUrl": "https://superagent.example.com/telegram/webhook"
    },
    "discord": {
      "enabled": false,
      "token": "${DISCORD_BOT_TOKEN}"
    },
    "whatsapp": {
      "enabled": false,
      "provider": "baileys"
    },
    "api": {
      "enabled": true,
      "cors": ["*"]
    }
  },

  // Binding rules
  "bindings": [
    {
      "match": { "channel": "telegram", "peer": "user:*" },
      "agentId": "queen"
    },
    {
      "match": {},
      "agentId": "queen"
    }
  ],

  // Model providers
  "providers": {
    "openai": {
      "apiKey": "${OPENAI_API_KEY}"
    },
    "anthropic": {
      "apiKey": "${ANTHROPIC_API_KEY}"
    },
    "openrouter": {
      "apiKey": "${OPENROUTER_API_KEY}"
    },
    "together": {
      "apiKey": "${TOGETHER_API_KEY}"
    }
  },

  // MCP servers
  "mcp": {
    "servers": [
      {
        "name": "github",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
        }
      }
    ]
  },

  // Memory configuration
  "memory": {
    "vectorStore": {
      "provider": "qdrant",
      "url": "http://qdrant:6333",
      "collections": [
        {
          "name": "agent_memory",
          "dimensions": 1536,
          "embedding": {
            "provider": "openai",
            "model": "text-embedding-3-small"
          }
        }
      ]
    },
    "knowledgeGraph": {
      "provider": "falkordb",
      "url": "redis://falkordb:6379"
    },
    "sessionSearch": {
      "provider": "fts5",
      "database": "./data/sessions.db"
    },
    "consolidation": {
      "interval": "24h",
      "autoCreateSkills": true
    }
  },

  // Learning engine
  "learning": {
    "enabled": true,
    "reflection": {
      "trigger": "post_task",
      "minToolCalls": 5
    },
    "skillCreation": {
      "enabled": true,
      "autoApprove": false,
      "storage": "./skills/auto-created/"
    },
    "memoryNudge": {
      "interval": "6h",
      "enabled": true
    }
  },

  // Kanban
  "kanban": {
    "enabled": true,
    "database": "./data/kanban.db",
    "dispatcher": {
      "interval": 60,
      "maxConcurrent": 5
    },
    "lanes": [
      { "id": "researcher", "model": "together/qwen3.5-9b" },
      { "id": "analyst", "model": "openai/gpt-4o" },
      { "id": "reporter", "model": "together/qwen3.5-9b" }
    ]
  },

  // Tool Gateway (Nous)
  "nousGateway": {
    "enabled": false,
    "apiKey": "${NOUS_GATEWAY_KEY}",
    "baseUrl": "https://gateway.nousresearch.com/v1",
    "tools": {
      "webSearch": true,
      "imageGeneration": true,
      "tts": true,
      "cloudBrowser": true
    }
  },

  // Tool policy
  "toolPolicy": {
    "defaultProfile": "coding",
    "profiles": {
      "minimal": {
        "allowed": ["read", "write", "web_search", "session_search", "memory_search"]
      },
      "coding": {
        "allowed": ["read", "write", "edit", "exec", "process", "web_search", "web_fetch", "session_search", "memory_search", "browser"]
      },
      "full": {
        "allowed": ["*"]
      }
    }
  },

  // Automation
  "automation": {
    "cron": {
      "enabled": true,
      "timezone": "Africa/Nairobi"
    },
    "heartbeat": {
      "enabled": true,
      "intervalMinutes": 30
    }
  },

  // Logging
  "logging": {
    "level": "info",
    "format": "json",
    "destination": "stdout"
  }
}
```

### 11.2 Environment Variables

```bash
# .env — Environment variables (DO NOT COMMIT)

# Gateway
GATEWAY_AUTH_TOKEN=your-secret-token-here

# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
TOGETHER_API_KEY=...

# Channels
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
DISCORD_BOT_TOKEN=...

# MCP
GITHUB_TOKEN=ghp_...

# Nous Tool Gateway
NOUS_GATEWAY_KEY=...

# Database
POSTGRES_PASSWORD=superagent-secure-password

# M-Pesa (future)
MPESA_CONSUMER_KEY=
MPESA_CONSUMER_SECRET=
```

---

## 12. API Reference

### 12.1 OpenAI-Compatible HTTP API

```yaml
# API Endpoints

POST /v1/chat/completions:
  description: OpenAI Chat Completions compatible endpoint
  body:
    model: string           # "queen", "market-intel", etc.
    messages: Message[]
    stream: boolean
    tools: Tool[]
    temperature: float
  response:
    id: string
    object: "chat.completion"
    choices: Choice[]
    usage: Usage

POST /v1/responses:
  description: OpenAI Responses API (stateful)
  body:
    model: string
    input: string | Message[]
    stream: boolean
  response:
    id: string
    output: Content[]

POST /v1/runs:
  description: Start a background run (returns 202)
  body:
    agent: string           # agent id
    task: string
    model: string (optional)
  response:
    run_id: string
    status: "queued"

GET /v1/runs/{id}:
  description: Get run status
  response:
    run_id: string
    status: "queued" | "running" | "completed" | "failed"
    result: string (when completed)

GET /v1/runs/{id}/events:
  description: SSE stream of run lifecycle events
  response: text/event-stream

GET /v1/models:
  description: List available models/agents
  response:
    data: Model[]

GET /v1/capabilities:
  description: Machine-readable feature flags
  response:
    streaming: boolean
    tools: boolean
    agents: string[]
    channels: string[]

GET /health:
  description: Health check
  response:
    status: "ok"
    version: string
    uptime: number
```

### 12.2 WebSocket API (from OpenClaw)

```typescript
// WebSocket connection
const ws = new WebSocket("ws://localhost:18789");

// Authenticate
ws.send(JSON.stringify({
  type: "req",
  id: "auth-1",
  method: "connect",
  params: {
    auth: { token: "your-token" },
    role: "client"
  }
}));

// Send message to agent
ws.send(JSON.stringify({
  type: "req",
  id: "msg-1",
  method: "agent",
  params: {
    message: "What are tomato prices in Nairobi?",
    sessionKey: "user:123456",
    agentId: "queen"
  }
}));

// Receive streamed response
ws.on("message", (data) => {
  const event = JSON.parse(data);
  if (event.type === "event" && event.event === "agent") {
    // Handle agent response chunks
  }
});
```

### 12.3 A2A Protocol Endpoints

```yaml
GET /.well-known/agent.json:
  description: Agent Card (A2A discovery)
  response: AgentCard

POST /a2a/tasks:
  description: Create a new A2A task
  body:
    message: Message
    metadata: object (optional)
  response:
    id: string
    status: "submitted"

GET /a2a/tasks/{id}:
  description: Get A2A task status
  response: Task

POST /a2a/tasks/{id}/cancel:
  description: Cancel an A2A task
  response: Task
```

---

## 13. Security Model

### 13.1 Security Layers

```
┌─────────────────────────────────────────────────────┐
│ LAYER 1: NETWORK                                    │
│ • WS on loopback by default                         │
│ • TLS for external connections                      │
│ • Tailscale/SSH tunnel for remote access            │
├─────────────────────────────────────────────────────┤
│ LAYER 2: AUTHENTICATION                             │
│ • Shared-secret for WS connections                  │
│ • Bearer token for HTTP API                         │
│ • Device pairing with cryptographic identity        │
│ • A2A signed Agent Cards                            │
├─────────────────────────────────────────────────────┤
│ LAYER 3: ACCESS CONTROL                             │
│ • Channel allowlists and DM pairing                 │
│ • Per-agent tool/skill allowlists                   │
│ • Exec approval for shell commands                  │
│ • Role-based Kanban access                          │
├─────────────────────────────────────────────────────┤
│ LAYER 4: TOOL SANDBOXING                            │
│ • Workspace isolation (agents can't escape)         │
│ • Network restrictions per agent                    │
│ • Tool policy enforced BEFORE model call            │
│ • Sub-agents get restricted tool sets               │
├─────────────────────────────────────────────────────┤
│ LAYER 5: DATA PROTECTION                            │
│ • External content marked as untrusted              │
│ • sessions_history returns redacted views           │
│ • Memory files scanned for injection patterns       │
│ • Knowledge graph entries validated                 │
├─────────────────────────────────────────────────────┤
│ LAYER 6: PROMPT SAFETY                              │
│ • System prompt boundaries enforced                 │
│ • Tool results sanitized before context injection   │
│ • Skill content validated on load                   │
│ • Anti-injection patterns in memory writes          │
└─────────────────────────────────────────────────────┘
```

### 13.2 Agent Isolation

Each agent gets its own:
- **Workspace directory** (can't read/write outside)
- **Session store** (own SQLite database)
- **Skill set** (filtered by allowlist)
- **Tool access** (filtered by policy)
- **Model configuration** (own provider keys optional)

### 13.3 Memory Security

```yaml
memory_security:
  injection_scan: true          # Scan memory writes for injection patterns
  exfiltration_scan: true       # Scan for data exfiltration attempts
  max_entry_size: 4096          # Max chars per memory entry
  approval_required: false      # Set true for production
  redaction_patterns:
    - "api_key"
    - "password"
    - "secret"
    - "token"
    - "private_key"
```

---

## 14. Build Phases

### Phase 1: Foundation (Weeks 1-4)

**Goal:** Working gateway with Telegram, basic agent loop, session storage.

```yaml
deliverables:
  - Gateway process (Node.js) with Telegram adapter
  - Agent runtime (Python) with model abstraction
  - Session storage (SQLite + FTS5)
  - Workspace file injection (AGENTS.md, SOUL.md, USER.md)
  - Basic tool system (exec, read, write, web_search, web_fetch)
  - Docker Compose deployment

mvp_features:
  - Single agent (Queen) responding on Telegram
  - Session persistence across restarts
  - Workspace memory (MEMORY.md, daily notes)
  - 5 built-in tools
  - Health check endpoint

cost: ~$17/mo (Fly.io + free-tier databases)
team: 1-2 developers
```

### Phase 2: Multi-Agent (Weeks 5-8)

**Goal:** Queen + swarm hierarchy, sub-agent spawning, skill system.

```yaml
deliverables:
  - Intent routing (Queen → Swarm classification)
  - Swarm leader agents (market-intel, info-network, coordination)
  - Sub-agent spawning (sessions_spawn with model override)
  - Skill loader with progressive disclosure
  - Tool policy pipeline (profiles, allowlists)
  - MCP client integration

new_features:
  - 3 swarm leaders with specialized skills
  - Worker agents spawned on-demand
  - 10+ bundled skills
  - MCP server connections (GitHub, filesystem)
  - Tool approval system

cost: ~$25/mo
team: 1-2 developers
```

### Phase 3: Memory & Knowledge (Weeks 9-12)

**Goal:** Vector DB, knowledge graph, hybrid search, memory consolidation.

```yaml
deliverables:
  - Qdrant vector store integration
  - FalkorDB knowledge graph integration
  - Hybrid search (FTS5 + vector + reranking)
  - Memory consolidation engine
  - Knowledge extraction pipeline (entities + relationships)
  - Cross-agent memory sharing

new_features:
  - Semantic search across all sessions
  - Knowledge graph queries ("find all tomato sellers near Kibera")
  - Automatic entity extraction from conversations
  - Memory nudge (periodic curation)
  - Cross-agent QMD collections

cost: ~$35/mo (Qdrant + FalkorDB in Docker)
team: 1-2 developers
```

### Phase 4: Learning & Self-Improvement (Weeks 13-16)

**Goal:** Reflection cycles, autonomous skill creation, Kanban board.

```yaml
deliverables:
  - Post-task reflection engine
  - Autonomous skill creation from experience
  - Skill self-improvement (patch, edit, version)
  - Kanban task board with worker lanes
  - Dispatcher loop for task assignment
  - Trajectory logging for training data

new_features:
  - Agent creates skills after complex tasks
  - Skills evolve through use
  - Durable task queue with crash recovery
  - Human-in-the-loop task blocking
  - Daily memory consolidation
  - Skill workshop (proposal queue)

cost: ~$40/mo
team: 1-2 developers
```

### Phase 5: Production & Scale (Weeks 17-20)

**Goal:** HTTP API, A2A protocol, monitoring, payment integration.

```yaml
deliverables:
  - OpenAI-compatible HTTP API server
  - A2A protocol endpoints (Agent Cards, tasks)
  - MCP Apps support
  - Monitoring (Helicone, Prometheus metrics)
  - M-Pesa payment integration
  - Multi-channel expansion (WhatsApp, Discord)

new_features:
  - Programmatic API access
  - Agent-to-agent communication (A2A)
  - Payment processing (M-Pesa STK Push)
  - Cost tracking and budgets
  - Alert/notification system
  - Voice message support (STT/TTS)

cost: ~$80/mo
team: 2-3 developers
```

### Phase 6: Edge & Scale (Weeks 21+)

**Goal:** Edge AI, mobile support, self-hosted models, multi-region.

```yaml
deliverables:
  - Edge AI runtime (llama.cpp integration)
  - Mobile companion app (React Native)
  - Self-hosted model support (Ollama, vLLM)
  - Multi-region deployment
  - Advanced analytics dashboard
  - Enterprise features (RBAC, audit logs)

future_features:
  - Offline-capable mobile agent
  - Self-hosted LLM for cost reduction
  - Multi-region Gateway instances
  - Agent marketplace (skills, tools)
  - Policy simulation engine
  - Cross-border agent commerce

cost: $150-500/mo
team: 3-5 developers
```

---

## Appendix A: Comparison — What Comes From Where

| Feature | OpenClaw | Hermes | SUPERAGENT (Merged) |
|---------|----------|--------|---------------------|
| Gateway process | ✅ Primary | ✅ Secondary | OpenClaw core + Hermes adapters |
| Channel adapters | 20+ | 20+ | Union of both (25+) |
| Session management | ✅ SQLite | ✅ SQLite+FTS5 | SQLite + FTS5 + vector |
| Agent runtime | ✅ Node.js | ✅ Python | Hybrid (Node gateway, Python agents) |
| Sub-agent spawning | ✅ sessions_spawn | ✅ delegate_task | OpenClaw pattern + Hermes batch mode |
| Memory: workspace files | ✅ | ✅ | OpenClaw files + Hermes frozen snapshot |
| Memory: session search | ✅ QMD | ✅ FTS5 | FTS5 + vector hybrid search |
| Memory: knowledge graph | ❌ | ❌ | New (FalkorDB) |
| Memory: vector DB | ⚠️ Optional | ❌ | Qdrant (new) |
| Skills: format | ✅ SKILL.md | ✅ SKILL.md | agentskills.io standard |
| Skills: progressive disclosure | ❌ | ✅ Level 0/1/2 | Hermes pattern |
| Skills: self-improvement | ❌ | ✅ Auto-patch | Hermes learning loop |
| Skills: workshop | ✅ Proposal queue | ❌ | OpenClaw governance |
| Skills: /learn | ❌ | ✅ | Hermes command |
| Kanban board | ❌ | ✅ | Hermes board |
| Reflection cycles | ❌ | ✅ | Hermes learning engine |
| Cron/scheduling | ✅ | ✅ | OpenClaw cron + Hermes scheduler |
| Heartbeat | ✅ | ❌ | OpenClaw heartbeat |
| HTTP API | ❌ | ✅ OpenAI-compat | Hermes API server |
| A2A protocol | ❌ | ❌ | New (spec implementation) |
| MCP client | ⚠️ Plugin | ✅ Built-in | Hermes MCP client |
| Tool Gateway (Nous) | ❌ | ✅ | Hermes gateway |
| Tool policy | ✅ Pipeline | ❌ | OpenClaw pipeline |
| Code mode | ✅ | ❌ | OpenClaw |
| Trajectory logging | ❌ | ✅ | Hermes |
| MoA (Mixture of Agents) | ❌ | ✅ | Hermes virtual model |
| Node system | ✅ | ❌ | OpenClaw nodes |

---

## Appendix B: Example Interaction Flow

**User:** "I have 30kg of tomatoes to sell in Kibera. What's the best price and can you find me buyers?"

```
1. Telegram adapter receives message
2. Session resolved → user:telegram:123456 → agent: queen
3. Queen loads context (AGENTS.md, SOUL.md, USER.md, MEMORY.md)
4. Queen classifies intent: ["price_query", "find_customer"]
5. Queen routes to market-intel swarm

6. market-intel swarm receives task
7. Spawns worker 1: "Research tomato prices in Kibera area"
   - Worker queries price database (SQLite)
   - Worker searches web for recent tomato prices
   - Worker returns: "Tomatoes: KSh 75-90/kg in Kibera area"

8. Spawns worker 2: "Find tomato buyers near Kibera"
   - Worker searches knowledge graph for buyers
   - Worker checks recent sessions for buyer queries
   - Worker returns: "3 potential buyers found"

9. market-intel aggregates results
10. Queen formats response:

    🍅 **Tomato Market Intelligence — Kibera**

    **Current Prices:**
    • Kibera Market: KSh 80/kg
    • Gikomba (wholesale): KSh 65/kg
    • Wakulima: KSh 85/kg

    **Recommendation:** Price at KSh 80/kg — competitive for retail.

    **Buyers Found:**
    👩 Amina — Looking for 20kg tomatoes, Kibera area
    👨 Peter — Restaurant owner, needs 50kg/week
    👩 Jane — Mama mboga, Eastleigh, needs 15kg

    Want me to connect you with any of these buyers?

11. Response sent via Telegram adapter
12. Interaction logged to session store
13. Knowledge graph updated:
    - (User)-[:SELLS]->(Product:tomatoes)
    - (User)-[:LOCATED_AT]->(Market:Kibera)
    - (Price:80)-[:AT_MARKET]->(Market:Kibera)
14. Learning engine queued for post-task reflection
```

---

## Appendix C: Example Cron Jobs

```jsonc
// Cron job configuration
{
  "jobs": [
    {
      "id": "daily-market-brief",
      "schedule": "0 7 * * *",
      "timezone": "Africa/Nairobi",
      "agent": "market-intel",
      "task": "Generate daily market brief for all tracked commodities. Include price changes, demand signals, and actionable recommendations.",
      "deliver": {
        "channel": "telegram",
        "to": "group:market-nairobi"
      },
      "skills": ["price-analysis", "demand-forecast"]
    },
    {
      "id": "price-collection-prompt",
      "schedule": "0 9 * * 1-5",
      "timezone": "Africa/Nairobi",
      "agent": "info-network",
      "task": "Send price collection survey to active users. Ask them to report current prices at their markets.",
      "deliver": {
        "channel": "telegram",
        "to": "group:price-reporters"
      }
    },
    {
      "id": "hourly-alert-check",
      "schedule": "*/60 * * * *",
      "agent": "info-network",
      "task": "Check all active price alerts. Trigger notifications for any threshold breaches.",
      "skills": ["alert-system"]
    },
    {
      "id": "weekly-memory-consolidation",
      "schedule": "0 2 * * 0",
      "agent": "queen",
      "task": "Review all interactions from the past week. Extract significant learnings. Update MEMORY.md. Identify skill creation opportunities.",
      "skills": ["memory-management"]
    }
  ]
}
```

---

## Appendix D: Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Gateway language | Node.js (TypeScript) | OpenClaw is Node.js; reuses existing channel adapters |
| Agent runtime | Python | Hermes is Python; best LLM ecosystem support |
| Inter-process comm | WebSocket + Redis | Gateway ↔ agents via WS; agents ↔ agents via Redis pub/sub |
| Primary database | PostgreSQL | Production-grade, supports FTS5, JSON, and relational queries |
| Session search | SQLite FTS5 (embedded) | Zero-latency for agent-local searches; no network hop |
| Vector store | Qdrant | Open-source, high-performance, filtering support |
| Knowledge graph | FalkorDB | Redis-compatible, ultra-low latency, graph queries |
| Skill format | Markdown (agentskills.io) | Open standard, portable, zero-code extensibility |
| Embedding model | text-embedding-3-small | Cheap ($0.02/1M tokens), 1536 dims, good quality |
| Worker model | Qwen3.5 9B via Together | $0.17/1M tokens, good enough for data collection |
| Queen model | Claude Sonnet 4 or GPT-4o | Best reasoning for orchestration |
| Deployment | Docker Compose on Fly.io | Simple, cheap, Africa region available |
| Payment | M-Pesa (Daraja API) | Dominant in Kenya, 30M+ users |

---

*This architecture is a living document. Update as the system is built, tested, and iterated upon.*

**Version History:**
- v1.0.0 (2026-07-22): Initial architecture specification
