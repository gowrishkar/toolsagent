#!/usr/bin/env python3
"""Ensure diary has ## YYYY-MM-DD and ### Actions for the log day."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
DIARY = Path.home() / ".hermes" / "diary.md"


def log_day(now: datetime | None = None) -> datetime:
    now = now or datetime.now(IST)
    if now.hour == 0 and now.minute < 45:
        return now - timedelta(days=1)
    return now


def audit(diary_path: Path = DIARY, now: datetime | None = None) -> dict:
    day = log_day(now)
    iso = day.strftime("%Y-%m-%d")
    weekday = day.strftime("%a")
    header = f"## {iso} ({weekday})"
    text = diary_path.read_text(encoding="utf-8") if diary_path.exists() else ""
    changed = False
    if header not in text and f"## {iso}" not in text:
        stamp = datetime.now(IST).strftime("%H:%M")
        block = (
            f"\n---\n\n{header}\n\n### Actions\n"
            f"- [{stamp}] [dream] Diary section auto-opened by DREAM audit\n\n"
            f"### Errors\n- (none)\n"
        )
        text = text.rstrip() + block
        changed = True
    elif f"## {iso}" in text and "### Actions" not in text.split(f"## {iso}", 1)[1].split("\n## ", 1)[0]:
        # rare: header without Actions
        text = text.replace(f"## {iso}", f"## {iso}\n\n### Actions\n- [dream] section repaired\n", 1)
        changed = True
    if changed:
        diary_path.parent.mkdir(parents=True, exist_ok=True)
        diary_path.write_text(text, encoding="utf-8")
    has_actions = "### Actions" in text and f"## {iso}" in text
    return {"day": iso, "changed": changed, "has_actions": has_actions}


if __name__ == "__main__":
    import json
    import sys

    print(json.dumps(audit(), indent=2))
    sys.exit(0)