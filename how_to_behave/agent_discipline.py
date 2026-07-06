"""Agent Discipline Layer

A tiny guardrail that stops AI agents from calling unfinished work done.

It creates a completion contract, collects evidence, detects lazy output, and
blocks final success reports until required checks are proven.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Evidence:
    """Proof for one done check."""

    check: str
    status: str = "passed"
    output: str = ""
    path: Optional[str] = None
    note: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    exists: Optional[bool] = None

    def __post_init__(self) -> None:
        if self.path:
            self.exists = Path(self.path).exists()
            if not self.exists and self.status == "passed":
                self.status = "failed"
                self.output = self.output or f"Path does not exist: {self.path}"

    @property
    def passed(self) -> bool:
        return self.status == "passed" and self.exists is not False


@dataclass
class CompletionContract:
    """Defines what done means for an agent task."""

    goal: str
    done_checks: List[str]
    evidence: Dict[str, List[Evidence]] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        self.done_checks = [check.strip() for check in self.done_checks if check.strip()]
        self.evidence = {check: self.evidence.get(check, []) for check in self.done_checks}


@dataclass
class FinishResult:
    """Result of the done gate."""

    allowed: bool
    missing: List[str]
    failed: List[str]
    lazy_flags: List[str] = field(default_factory=list)
    report: str = ""


class AgentDisciplineLayer:
    """Completion and anti-laziness layer for AI agents."""

    done_words = ("done", "finished", "complete", "completed", "ready", "fixed", "built")
    vague_success_phrases = (
        "should work",
        "should be working",
        "looks good",
        "all set",
        "basically done",
        "probably works",
    )

    def create_contract(self, goal: str, done_checks: List[str]) -> CompletionContract:
        if not goal.strip():
            raise ValueError("goal is required")
        if not done_checks:
            raise ValueError("at least one done check is required")
        return CompletionContract(goal=goal.strip(), done_checks=done_checks)

    def add_evidence(
        self,
        contract: CompletionContract,
        check: str,
        *,
        status: str = "passed",
        output: str = "",
        path: Optional[str] = None,
        note: str = "",
    ) -> Evidence:
        if check not in contract.done_checks:
            raise ValueError(f"Unknown done check: {check}")
        evidence = Evidence(check=check, status=status, output=output, path=path, note=note)
        contract.evidence.setdefault(check, []).append(evidence)
        return evidence

    def can_finish(
        self,
        contract: CompletionContract,
        *,
        final_message: str = "",
        tool_calls_made: bool = True,
    ) -> FinishResult:
        missing: List[str] = []
        failed: List[str] = []

        for check in contract.done_checks:
            items = contract.evidence.get(check, [])
            if not items:
                missing.append(check)
                continue
            if not any(item.passed for item in items):
                failed.append(check)

        lazy_flags = self.detect_laziness(
            message=final_message,
            evidence=[item for items in contract.evidence.values() for item in items],
            tool_calls_made=tool_calls_made,
        ) if final_message else []

        allowed = not missing and not failed and not lazy_flags
        report = self._render_report(contract, allowed, missing, failed, lazy_flags)
        return FinishResult(
            allowed=allowed,
            missing=missing,
            failed=failed,
            lazy_flags=lazy_flags,
            report=report,
        )

    def detect_laziness(
        self,
        *,
        message: str,
        evidence: List[Evidence],
        tool_calls_made: bool,
    ) -> List[str]:
        text = message.lower()
        flags: List[str] = []

        claims_done = any(word in text for word in self.done_words)
        has_passed_evidence = any(item.passed for item in evidence)

        if claims_done and not has_passed_evidence:
            flags.append("claimed_done_without_evidence")
        if not tool_calls_made:
            flags.append("no_tool_calls")
        if any(phrase in text for phrase in self.vague_success_phrases):
            flags.append("vague_success_language")
        if "you can run" in text and not has_passed_evidence:
            flags.append("delegated_verification_to_user")

        return flags

    def next_action(self, contract: CompletionContract) -> str:
        result = self.can_finish(contract)
        if result.failed:
            return f"Fix failed check: {result.failed[0]}"
        if result.missing:
            return f"Collect evidence for: {result.missing[0]}"
        if result.lazy_flags:
            return f"Resolve lazy flag: {result.lazy_flags[0]}"
        return "Ready to report completion."

    def _render_report(
        self,
        contract: CompletionContract,
        allowed: bool,
        missing: List[str],
        failed: List[str],
        lazy_flags: List[str],
    ) -> str:
        lines = [
            f"Goal: {contract.goal}",
            f"Can finish: {allowed}",
        ]
        if missing:
            lines.append("Missing: " + ", ".join(missing))
        if failed:
            lines.append("Failed: " + ", ".join(failed))
            for check in failed:
                latest = contract.evidence.get(check, [])[-1]
                if latest.output:
                    lines.append(f"- {check}: {latest.output}")
        if lazy_flags:
            lines.append("Lazy flags: " + ", ".join(lazy_flags))
        if allowed:
            lines.append("All done checks have passing evidence.")
        return "\n".join(lines)
