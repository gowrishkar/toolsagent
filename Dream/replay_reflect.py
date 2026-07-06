#!/usr/bin/env python3
"""Build trajectory from diary and run Submind reflect (success + failures)."""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DIARY = Path.home() / ".hermes" / "diary.md"
HERMES_STATE = Path.home() / ".hermes" / "toolsagent"
REFLECT = REPO / "hermes" / "reflect_run.py"


def _day_header(iso: str, text: str) -> str:
    m = re.search(rf"## {re.escape(iso)}[^\n]*", text)
    if not m:
        return ""
    chunk = text[m.start() :]
    nxt = re.search(r"\n## \d{4}-\d{2}-\d{2}", chunk[1:])
    if nxt:
        chunk = chunk[: nxt.start() + 1]
    return chunk


def _section(chunk: str, name: str) -> list[str]:
    lines: list[str] = []
    in_sec = False
    for raw in chunk.splitlines():
        if raw.strip() == f"### {name}":
            in_sec = True
            continue
        if in_sec and raw.startswith("### "):
            break
        if in_sec and raw.strip().startswith("- "):
            body = raw.strip()[2:].strip()
            if body.lower() in ("(none)", "none"):
                continue
            lines.append(body)
    return lines


def replay(iso_day: str) -> dict:
    text = DIARY.read_text(encoding="utf-8") if DIARY.exists() else ""
    chunk = _day_header(iso_day, text)
    errors = _section(chunk, "Errors")
    actions = _section(chunk, "Actions")
    wins = [{"action": "daily_action", "result": a[:200]} for a in actions[:20]]
    fails = [{"action": "diary_error", "result": e[:200]} for e in errors[:10]]
    return {"wins": wins, "fails": fails, "action_count": len(actions), "error_count": len(errors)}


def _run_reflect(trajectory: list[dict], failed: bool) -> None:
    if not trajectory:
        return
    HERMES_STATE.mkdir(parents=True, exist_ok=True)
    tmp = HERMES_STATE / "dream_trajectory.json"
    tmp.write_text(json.dumps(trajectory), encoding="utf-8")
    cmd = [sys.executable, str(REFLECT), str(tmp)]
    if failed:
        cmd.append("--failed")
    subprocess.run(cmd, check=False, cwd=str(REPO), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def reflect_day(iso_day: str) -> dict:
    data = replay(iso_day)
    if data["wins"]:
        _run_reflect(data["wins"], failed=False)
    if data["fails"]:
        _run_reflect(data["fails"], failed=True)
    return data


if __name__ == "__main__":
    from diary_audit import log_day

    iso = log_day().strftime("%Y-%m-%d")
    print(json.dumps(reflect_day(iso), indent=2))