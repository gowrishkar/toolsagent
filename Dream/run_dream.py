#!/usr/bin/env python3
"""
DREAM orchestrator: diary → reflect → hermes update → backup → Drive upload.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
DREAM_DIR = Path(__file__).resolve().parent
HERMES_DREAM = Path.home() / ".hermes" / "dream"
REPORTS = HERMES_DREAM / "reports"
GITHUB_PRESENCE = Path.home() / ".hermes" / "scripts" / "daily-github-presence.py"

sys.path.insert(0, str(DREAM_DIR))
from diary_audit import audit, log_day  # noqa: E402
from replay_reflect import reflect_day  # noqa: E402
from backup import create_backup, hermes_update  # noqa: E402
from upload import upload_file  # noqa: E402


def run_build_log() -> dict:
    if not GITHUB_PRESENCE.exists():
        return {"skipped": True, "reason": "no daily-github-presence.py"}
    proc = subprocess.run(
        [sys.executable, str(GITHUB_PRESENCE)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    return {
        "exit_code": proc.returncode,
        "stdout": (proc.stdout or "").strip()[-300:],
        "stderr": (proc.stderr or "").strip()[-300:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="DREAM nightly pipeline")
    ap.add_argument("--dry-run", action="store_true", help="Skip hermes update and Drive upload")
    ap.add_argument("--skip-build-log", action="store_true")
    args = ap.parse_args()

    day = log_day()
    iso = day.strftime("%Y-%m-%d")
    report: dict = {"day": iso, "started": datetime.now(IST).isoformat(), "phases": {}}

    report["phases"]["diary_audit"] = audit()
    report["phases"]["reflect"] = reflect_day(iso)

    if not args.skip_build_log:
        report["phases"]["build_log"] = run_build_log()
    else:
        report["phases"]["build_log"] = {"skipped": True}

    report["phases"]["hermes_update"] = hermes_update(skip=args.dry_run)

    tar_path = create_backup(iso)
    report["phases"]["backup"] = {"path": str(tar_path), "bytes": tar_path.stat().st_size}

    if args.dry_run:
        report["phases"]["upload"] = {"skipped": True, "dry_run": True}
    else:
        report["phases"]["upload"] = upload_file(tar_path)

    report["finished"] = datetime.now(IST).isoformat()
    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / f"{iso}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    ok = report["phases"].get("upload", {}).get("ok", True) or report["phases"]["upload"].get("skipped")
    update_ok = report["phases"]["hermes_update"].get("exit_code", 0) == 0 or report["phases"]["hermes_update"].get("skipped")
    print(json.dumps({"dream": "ok" if ok and update_ok else "partial", "report": str(out)}, indent=2))
    return 0 if ok and update_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())