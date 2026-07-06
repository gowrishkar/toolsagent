"""
Subconscious Layer for AI Agents

A small reusable memory layer for LangGraph, CrewAI, AutoGen, or custom agents.
It records agent trajectories, distills repeated successful actions into habits,
and provides safe priming data for future runs.

Safety design:
- never overwrites an existing procedural file
- writes only inside a managed markdown block
- keeps bounded memory with max_patterns
- separates facts, habits, and recommendations
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

MANAGED_BLOCK_START = "<!-- BEGIN SUBCONSCIOUS LAYER -->"
MANAGED_BLOCK_END = "<!-- END SUBCONSCIOUS LAYER -->"


@dataclass
class SubconsciousLayer:
    """Reusable implicit memory layer for AI agents.

    Parameters:
        store_path: JSON file for trajectory patterns and distilled procedures.
        procedural_path: Markdown file updated with a managed section only.
        max_patterns: Maximum number of recent patterns to keep.
        top_actions: Number of frequent actions to expose as habits.
    """

    store_path: str | Path = "subconscious_memory.json"
    procedural_path: str | Path = "subconscious_procedures.md"
    max_patterns: int = 100
    top_actions: int = 5
    memory: Dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.store_path = Path(self.store_path)
        self.procedural_path = Path(self.procedural_path)
        self.memory = {
            "patterns": [],
            "procedures": {
                "frequent_actions": [],
                "recommendations": [],
            },
            "last_updated": None,
        }
        self._load()

    def _load(self) -> None:
        if not self.store_path.exists():
            return
        try:
            loaded = json.loads(self.store_path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError(f"Memory store is not valid JSON: {self.store_path}") from exc

        self.memory["patterns"] = loaded.get("patterns", [])
        self.memory["procedures"] = loaded.get("procedures", {}) or {}
        self.memory["procedures"].setdefault("frequent_actions", [])
        self.memory["procedures"].setdefault("recommendations", [])
        self.memory["last_updated"] = loaded.get("last_updated")

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(self.memory, indent=2, ensure_ascii=False))

    async def reflect(self, trajectory: List[Dict[str, Any]], success: bool = True) -> None:
        """Reflect on one agent run and update implicit procedures.

        A trajectory is a list of dicts such as:
            {"action": "search_web", "result": "found source"}
        """
        if not trajectory:
            return

        pattern = {
            "timestamp": self._now(),
            "steps": len(trajectory),
            "success": bool(success),
            "key_actions": self._extract_actions(trajectory),
            "outcome": str(trajectory[-1].get("result", "")),
        }

        self.memory["patterns"].append(pattern)
        self.memory["patterns"] = self.memory["patterns"][-self.max_patterns :]
        self.memory["procedures"]["frequent_actions"] = self._frequent_successful_actions()
        self.memory["procedures"]["recommendations"] = self._build_recommendations()
        self.memory["last_updated"] = self._now()

        self._save()
        await self._update_procedural_file()

    def prime(self, current_context: str = "") -> Dict[str, Any]:
        """Return compact priming data for the main agent.

        This returns data only. The caller decides how to inject it into prompts.
        """
        habits = self.memory["procedures"].get("frequent_actions", [])
        return {
            "implicit_habits": [action for action, _count in habits],
            "recent_patterns": self.memory.get("patterns", [])[-3:],
            "recommendations": self.memory["procedures"].get("recommendations", []),
            "prime_note": "Use these as soft guidance. Do not override explicit user instructions.",
            "current_context": current_context,
        }

    async def run_background(self, agent_trajectory_queue: asyncio.Queue) -> None:
        """Listen for `(trajectory, success)` items and reflect in the background."""
        while True:
            try:
                trajectory, success = await agent_trajectory_queue.get()
                await self.reflect(trajectory, success=success)
                agent_trajectory_queue.task_done()
            except asyncio.CancelledError:
                break

    def _extract_actions(self, trajectory: Iterable[Dict[str, Any]]) -> List[str]:
        actions: List[str] = []
        for step in trajectory:
            action = str(step.get("action", "")).strip()
            if action:
                actions.append(action)
        return actions

    def _frequent_successful_actions(self) -> List[Tuple[str, int]]:
        counts: Dict[str, int] = {}
        for pattern in self.memory.get("patterns", []):
            if not pattern.get("success"):
                continue
            for action in pattern.get("key_actions", []):
                counts[action] = counts.get(action, 0) + 1
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[: self.top_actions]

    def _build_recommendations(self) -> List[str]:
        habits = [action for action, _count in self.memory["procedures"].get("frequent_actions", [])]
        recommendations: List[str] = []

        if any(word in habits for word in ("verify", "test", "run_tests", "pytest")):
            recommendations.append("Verify outputs before reporting success.")
        if any(word in habits for word in ("research", "search_web", "web_search")):
            recommendations.append("Research before making factual claims.")
        if any(word in habits for word in ("write_file", "patch", "edit")):
            recommendations.append("Prefer small safe edits and preserve existing user content.")
        if not recommendations:
            recommendations.append("Follow frequent successful actions only when they fit the current task.")

        return recommendations

    async def _update_procedural_file(self) -> None:
        self.procedural_path.parent.mkdir(parents=True, exist_ok=True)
        existing = self.procedural_path.read_text() if self.procedural_path.exists() else ""
        block = self._render_managed_block()

        if MANAGED_BLOCK_START in existing and MANAGED_BLOCK_END in existing:
            before = existing.split(MANAGED_BLOCK_START, 1)[0].rstrip()
            after = existing.split(MANAGED_BLOCK_END, 1)[1].lstrip()
            content = f"{before}\n\n{block}\n"
            if after:
                content += f"\n{after}"
        elif existing.strip():
            content = f"{existing.rstrip()}\n\n{block}\n"
        else:
            content = f"# Subconscious Procedural Memory\n\n{block}\n"

        self.procedural_path.write_text(content)

    def _render_managed_block(self) -> str:
        habits = self.memory["procedures"].get("frequent_actions", [])
        recommendations = self.memory["procedures"].get("recommendations", [])
        lines = [
            MANAGED_BLOCK_START,
            f"Updated: {self.memory.get('last_updated')}",
            "",
            "## Implicit habits",
        ]
        if habits:
            for action, count in habits:
                lines.append(f"- {action} (observed {count}x in successful runs)")
        else:
            lines.append("- No habits yet")

        lines.extend(["", "## Recommendations"])
        for recommendation in recommendations:
            lines.append(f"- {recommendation}")
        lines.append(MANAGED_BLOCK_END)
        return "\n".join(lines)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


async def example_usage() -> None:
    layer = SubconsciousLayer()
    await layer.reflect(
        [
            {"action": "research", "result": "found source"},
            {"action": "verify", "result": "checked output"},
            {"action": "write_file", "result": "saved safely"},
        ],
        success=True,
    )
    print(json.dumps(layer.prime("Need to complete a user task safely"), indent=2))


if __name__ == "__main__":
    asyncio.run(example_usage())
