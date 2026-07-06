"""Tests for DREAM diary helpers."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Dream"))

from diary_audit import log_day  # noqa: E402
from replay_reflect import _section  # noqa: E402


def test_section_parses_actions():
    chunk = "### Actions\n- [10:00] [test] did thing\n### Errors\n- (none)\n"
    assert len(_section(chunk, "Actions")) == 1


def test_log_day_returns_datetime():
    d = log_day()
    assert d.year >= 2026