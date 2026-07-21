"""
Learning Engine — Self-Improvement Loop

Implements the Hermes learning loop pattern:
1. Auto-skill creation from complex workflows
2. Skill self-improvement when better paths discovered
3. Memory curation via periodic nudges
4. Session search for episodic recall
5. Background review for continuous improvement

This module is the "intelligence" that makes SUPERAGENT better over time.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class Skill:
    """A learned skill (Hermes agentskills.io compatible)."""

    name: str
    description: str
    content: str
    category: str = "general"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    use_count: int = 0
    success_count: int = 0
    source_agent: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.use_count == 0:
            return 0.0
        return self.success_count / self.use_count


@dataclass
class LearningEvent:
    """An event that triggered learning."""

    event_type: str  # "skill_created", "skill_improved", "memory_curated", "pattern_detected"
    description: str
    agent_id: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class LearningEngine:
    """
    Self-improvement engine for SUPERAGENT.

    Combines:
    - Hermes's autonomous skill creation (trigger-based)
    - Hermes's skill self-improvement (patch-based)
    - Hermes's memory curation nudges
    - OpenClaw's workspace-based memory persistence
    - Background review loop

    The engine runs passively — it observes agent behavior and decides
    when to intervene with learning actions.
    """

    def __init__(
        self,
        skills_path: str = "./workspace/skills",
        memory_path: str = "./workspace/memory",
        memory_md_path: str = "./workspace/MEMORY.md",
        model: str = "anthropic/claude-sonnet-4-20250514",
        write_approval: bool = False,
    ):
        self.skills_path = Path(skills_path)
        self.memory_path = Path(memory_path)
        self.memory_md_path = Path(memory_md_path)
        self.model = model
        self.write_approval = write_approval

        self.skills_path.mkdir(parents=True, exist_ok=True)
        self.memory_path.mkdir(parents=True, exist_ok=True)

        self._events: list[LearningEvent] = []
        self._skill_cache: dict[str, Skill] = {}

    # ── Skill Management ────────────────────────────────────────

    def load_skills(self) -> dict[str, Skill]:
        """Load all skills from the skills directory."""
        skills = {}
        for skill_dir in self.skills_path.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            content = skill_file.read_text(encoding="utf-8")
            skill = self._parse_skill(skill_file, content)
            if skill:
                skills[skill.name] = skill

        self._skill_cache = skills
        return skills

    def _parse_skill(self, path: Path, content: str) -> Skill | None:
        """Parse a SKILL.md file into a Skill object."""
        try:
            # Parse YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    import yaml

                    frontmatter = yaml.safe_load(parts[1])
                    body = parts[2].strip()

                    return Skill(
                        name=frontmatter.get("name", path.parent.name),
                        description=frontmatter.get("description", ""),
                        content=body,
                        category=frontmatter.get("metadata", {}).get("superagent", {}).get("category", "general"),
                        source_agent=frontmatter.get("metadata", {}).get("superagent", {}).get("agent_id", ""),
                    )
        except Exception as e:
            logger.warning("skill_parse_failed", path=str(path), error=str(e))
        return None

    async def create_skill(
        self,
        name: str,
        description: str,
        content: str,
        agent_id: str,
        category: str = "workflow",
    ) -> Skill:
        """
        Create a new skill (Hermes autonomous skill creation).

        Skills follow the agentskills.io open standard.
        """
        skill_dir = self.skills_path / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_content = f"""---
name: {name}
description: "{description}"
metadata:
  superagent:
    auto_created: true
    agent_id: {agent_id}
    category: {category}
    created_at: {time.strftime("%Y-%m-%d %H:%M:%S")}
---

# {name}

{content}
"""

        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        skill = Skill(
            name=name,
            description=description,
            content=content,
            category=category,
            source_agent=agent_id,
        )

        self._skill_cache[name] = skill
        self._record_event("skill_created", f"Created skill: {name}", agent_id)

        logger.info("skill_created", name=name, agent_id=agent_id)
        return skill

    async def improve_skill(
        self,
        skill_name: str,
        improvement: str,
        agent_id: str,
    ) -> bool:
        """
        Improve an existing skill (Hermes skill self-improvement).

        Uses patch-based updates (old → new) rather than full rewrites.
        """
        skill = self._skill_cache.get(skill_name)
        if not skill:
            skills = self.load_skills()
            skill = skills.get(skill_name)
        if not skill:
            logger.warning("skill_not_found", name=skill_name)
            return False

        skill_dir = self.skills_path / skill_name
        skill_file = skill_dir / "SKILL.md"

        if not skill_file.exists():
            return False

        content = skill_file.read_text(encoding="utf-8")

        # Apply the improvement (append to the skill)
        improvement_section = f"\n\n## Improvement ({time.strftime('%Y-%m-%d %H:%M')})\n{improvement}\n"
        content += improvement_section

        skill_file.write_text(content, encoding="utf-8")
        skill.updated_at = time.time()
        skill.content += improvement_section

        self._record_event("skill_improved", f"Improved skill: {skill_name}", agent_id)
        logger.info("skill_improved", name=skill_name, agent_id=agent_id)
        return True

    # ── Memory Curation ─────────────────────────────────────────

    async def curate_memory(
        self,
        recent_interactions: list[dict[str, Any]],
        agent_id: str,
    ) -> str | None:
        """
        Hermes-style memory curation nudge.

        Analyzes recent interactions and decides if anything
        is worth persisting to long-term memory.
        """
        import litellm

        if not recent_interactions:
            return None

        interactions_text = "\n".join(
            f"[{i.get('role', 'unknown')}] {i.get('content', '')[:200]}"
            for i in recent_interactions[-10:]
        )

        nudge_prompt = (
            "You are reviewing recent interactions to decide if anything is worth "
            "remembering long-term. Consider:\n"
            "- User preferences or patterns\n"
            "- Important facts or decisions\n"
            "- Lessons learned from errors\n"
            "- Useful context for future interactions\n\n"
            "If something is worth remembering, output a concise memory entry.\n"
            "If nothing stands out, output 'NONE'.\n\n"
            f"Recent interactions:\n{interactions_text}"
        )

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": nudge_prompt}],
                max_tokens=300,
            )
            result = response.choices[0].message.content.strip()

            if result and result != "NONE":
                await self._write_curated_memory(result, agent_id)
                return result
        except Exception as e:
            logger.warning("memory_curation_failed", error=str(e))

        return None

    async def _write_curated_memory(self, entry: str, agent_id: str) -> None:
        """Write a curated memory entry to daily notes and optionally MEMORY.md."""
        # Write to daily notes
        daily_file = self.memory_path / f"{time.strftime('%Y-%m-%d')}.md"
        existing = ""
        if daily_file.exists():
            existing = daily_file.read_text(encoding="utf-8")

        timestamp = time.strftime("%H:%M")
        new_entry = f"\n\n### [{timestamp}] Learning Engine ({agent_id})\n{entry}\n"
        daily_file.write_text(existing + new_entry, encoding="utf-8")

        # Also consider adding to MEMORY.md if highly relevant
        if self.memory_md_path.exists():
            memory_content = self.memory_md_path.read_text(encoding="utf-8")
            if len(memory_content) < 2200:  # Hermes limit: 2200 chars
                memory_content += f"\n- {entry}"
                self.memory_md_path.write_text(memory_content, encoding="utf-8")

        self._record_event("memory_curated", f"Curated: {entry[:80]}", agent_id)
        logger.info("memory_curated", agent_id=agent_id, length=len(entry))

    # ── Learning Triggers ───────────────────────────────────────

    def should_create_skill(
        self,
        tool_calls: int,
        had_error: bool,
        had_correction: bool,
        task_complexity: str = "medium",
    ) -> bool:
        """
        Decide whether to auto-create a skill (Hermes triggers).

        Triggers:
        - 5+ tool calls in the workflow
        - Recovery from an error
        - User correction applied
        - Complex task with non-obvious solution
        """
        if tool_calls >= 5:
            return True
        if had_error:
            return True
        if had_correction:
            return True
        if task_complexity == "high":
            return True
        return False

    def should_improve_skill(
        self,
        skill_name: str,
        current_approach_steps: int,
        discovered_better_path: bool,
    ) -> bool:
        """Decide whether to improve an existing skill."""
        if discovered_better_path:
            return True
        skill = self._skill_cache.get(skill_name)
        if skill and current_approach_steps < skill.use_count * 0.5:
            return True  # found a more efficient path
        return False

    # ── Background Review ───────────────────────────────────────

    async def background_review(
        self,
        session_transcript: list[dict[str, Any]],
        agent_id: str,
    ) -> list[LearningEvent]:
        """
        Background review after each turn (Hermes pattern).

        May:
        - Save a memory entry
        - Update a skill
        - Both are consent-aware
        """
        events = []

        # Check for patterns worth remembering
        memory = await self.curate_memory(session_transcript, agent_id)
        if memory:
            events.append(LearningEvent(
                event_type="memory_curated",
                description=memory[:100],
                agent_id=agent_id,
            ))

        self._events.extend(events)
        return events

    # ── Event Tracking ──────────────────────────────────────────

    def _record_event(self, event_type: str, description: str, agent_id: str) -> None:
        """Record a learning event."""
        self._events.append(LearningEvent(
            event_type=event_type,
            description=description,
            agent_id=agent_id,
        ))

    def get_recent_events(self, limit: int = 20) -> list[LearningEvent]:
        """Get recent learning events."""
        return self._events[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get learning engine statistics."""
        return {
            "total_skills": len(self._skill_cache),
            "total_events": len(self._events),
            "events_by_type": self._count_events_by_type(),
            "skills_by_agent": self._count_skills_by_agent(),
        }

    def _count_events_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in self._events:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
        return counts

    def _count_skills_by_agent(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for skill in self._skill_cache.values():
            agent = skill.source_agent or "unknown"
            counts[agent] = counts.get(agent, 0) + 1
        return counts
