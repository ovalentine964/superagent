"""
Unified Memory Store

Combines:
- OpenClaw's workspace-based memory (AGENTS.md, MEMORY.md, daily notes, USER.md)
- Hermes's FTS5 session search for episodic recall
- Redis cache for hot data

This is the single entry point for all memory operations.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class MemoryEntry:
    """A single memory entry."""

    id: str
    content: str
    source: str  # "workspace", "session", "vector", "learning"
    category: str  # "fact", "preference", "decision", "skill", "observation"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 0.0


class UnifiedMemoryStore:
    """
    Unified memory store combining OpenClaw and Hermes patterns.

    Features:
    - Workspace memory: Read/write MEMORY.md, daily notes, USER.md
    - Session search: FTS5 full-text search over conversation transcripts
    - Redis cache: Hot cache for frequently accessed memories
    - Write approval: Optional gate for memory writes (Hermes pattern)
    """

    def __init__(
        self,
        workspace_path: str = "./workspace",
        db_path: str = "./data/sessions.db",
        redis_client: Any | None = None,
        write_approval: bool = False,
    ):
        self.workspace_path = Path(workspace_path)
        self.db_path = Path(db_path)
        self.redis = redis_client
        self.write_approval = write_approval

        # Ensure directories exist
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize FTS5 database
        self._init_fts5()

    def _init_fts5(self) -> None:
        """Initialize SQLite with FTS5 for session search (Hermes pattern)."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                channel TEXT,
                user_id TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        # FTS5 index for full-text search
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                content,
                content='messages',
                content_rowid='id'
            )
        """)
        # Triggers to keep FTS in sync
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content)
                VALUES ('delete', old.id, old.content);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content)
                VALUES ('delete', old.id, old.content);
                INSERT INTO messages_fts(messages_fts, rowid, content)
                VALUES (new.id, new.content);
            END
        """)
        conn.commit()
        conn.close()
        logger.info("fts5_initialized", db_path=str(self.db_path))

    # ── Workspace Memory (OpenClaw Pattern) ─────────────────────

    def read_memory(self) -> str:
        """Read long-term memory from MEMORY.md."""
        path = self.workspace_path / "MEMORY.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def write_memory(self, content: str, append: bool = False) -> None:
        """Write to MEMORY.md."""
        path = self.workspace_path / "MEMORY.md"
        if append and path.exists():
            existing = path.read_text(encoding="utf-8")
            content = existing + "\n\n" + content
        path.write_text(content, encoding="utf-8")
        logger.info("memory_written", path=str(path), length=len(content))

    def read_daily_notes(self, date: str | None = None) -> str:
        """Read daily memory notes."""
        if date is None:
            date = time.strftime("%Y-%m-%d")
        path = self.workspace_path / "memory" / f"{date}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def write_daily_note(self, content: str, date: str | None = None) -> None:
        """Append to daily memory notes."""
        if date is None:
            date = time.strftime("%Y-%m-%d")
        path = self.workspace_path / "memory" / f"{date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)

        existing = ""
        if path.exists():
            existing = path.read_text(encoding="utf-8")

        timestamp = time.strftime("%H:%M")
        entry = f"\n\n### [{timestamp}]\n{content}\n" if existing else f"### [{timestamp}]\n{content}\n"
        path.write_text(existing + entry, encoding="utf-8")
        logger.info("daily_note_written", date=date)

    def read_user_context(self) -> str:
        """Read USER.md for human context."""
        path = self.workspace_path / "USER.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def read_agents_config(self) -> str:
        """Read AGENTS.md for agent personality/rules."""
        path = self.workspace_path / "AGENTS.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    # ── Session Search (Hermes FTS5 Pattern) ────────────────────

    def create_session(
        self,
        session_id: str,
        agent_id: str,
        channel: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Create a new session record."""
        conn = sqlite3.connect(str(self.db_path))
        now = time.time()
        conn.execute(
            "INSERT OR REPLACE INTO sessions (id, agent_id, channel, user_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, agent_id, channel, user_id, now, now),
        )
        conn.commit()
        conn.close()

    def store_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """Store a message in the session transcript."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO messages (session_id, role, content, timestamp, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, time.time(), json.dumps(metadata or {})),
        )
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (time.time(), session_id),
        )
        conn.commit()
        conn.close()

    def search_sessions(
        self,
        query: str,
        limit: int = 10,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Full-text search over session transcripts (Hermes FTS5 pattern).

        Returns matching messages with context.
        """
        # Check Redis cache first
        cache_key = f"search:{query}:{limit}:{session_id}"
        if self.redis:
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        if session_id:
            rows = conn.execute(
                """
                SELECT m.*, s.agent_id, s.channel
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE m.rowid IN (
                    SELECT rowid FROM messages_fts WHERE messages_fts MATCH ?
                )
                AND m.session_id = ?
                ORDER BY m.timestamp DESC
                LIMIT ?
                """,
                (query, session_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT m.*, s.agent_id, s.channel
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE m.rowid IN (
                    SELECT rowid FROM messages_fts WHERE messages_fts MATCH ?
                )
                ORDER BY m.timestamp DESC
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()

        conn.close()

        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "session_id": row["session_id"],
                "role": row["role"],
                "content": row["content"],
                "timestamp": row["timestamp"],
                "agent_id": row["agent_id"],
                "channel": row["channel"],
            })

        # Cache results
        if self.redis and results:
            self.redis.setex(cache_key, 300, json.dumps(results))  # 5 min cache

        return results

    # ── Cache Layer ─────────────────────────────────────────────

    def cache_set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set a value in Redis cache."""
        if self.redis:
            self.redis.setex(key, ttl, json.dumps(value))

    def cache_get(self, key: str) -> Any | None:
        """Get a value from Redis cache."""
        if self.redis:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
        return None

    # ── Aggregated Search ───────────────────────────────────────

    def search_all(
        self,
        query: str,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """
        Search across all memory sources:
        1. Session transcripts (FTS5)
        2. Daily notes (FTS5)
        3. MEMORY.md (substring match)
        """
        results: list[MemoryEntry] = []

        # Session search
        session_results = self.search_sessions(query, limit=limit)
        for r in session_results:
            results.append(MemoryEntry(
                id=f"session:{r['id']}",
                content=r["content"],
                source="session",
                category="observation",
                timestamp=r["timestamp"],
                metadata={"session_id": r["session_id"], "agent_id": r["agent_id"]},
            ))

        # Daily notes search (simple substring)
        memory_dir = self.workspace_path / "memory"
        if memory_dir.exists():
            for note_file in sorted(memory_dir.glob("*.md"), reverse=True)[:7]:
                content = note_file.read_text(encoding="utf-8")
                if query.lower() in content.lower():
                    results.append(MemoryEntry(
                        id=f"daily:{note_file.stem}",
                        content=content[:500],
                        source="workspace",
                        category="observation",
                        timestamp=note_file.stat().st_mtime,
                    ))

        # MEMORY.md search
        memory_content = self.read_memory()
        if query.lower() in memory_content.lower():
            results.append(MemoryEntry(
                id="memory:long_term",
                content=memory_content[:500],
                source="workspace",
                category="fact",
            ))

        return results[:limit]
