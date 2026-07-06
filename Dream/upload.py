#!/usr/bin/env python3
"""Upload backup archive to Google Drive Archive folder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

KNOWLEDGE = Path.home() / ".hermes" / "knowledge-drive.json"
GOOGLE_API = (
    Path.home()
    / ".hermes"
    / "skills"
    / "productivity"
    / "google-workspace"
    / "scripts"
    / "google_api.py"
)


def archive_folder_id() -> str:
    data = json.loads(KNOWLEDGE.read_text(encoding="utf-8"))
    return data["folders"]["Archive"]


def upload_file(local_path: Path, name: str | None = None) -> dict:
    if not GOOGLE_API.exists():
        raise FileNotFoundError(f"google_api.py not found: {GOOGLE_API}")
    parent = archive_folder_id()
    cmd = [
        sys.executable,
        str(GOOGLE_API),
        "drive",
        "upload",
        str(local_path),
        "--parent",
        parent,
    ]
    if name:
        cmd.extend(["--name", name])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if proc.returncode != 0:
        return {"ok": False, "stderr": proc.stderr, "stdout": proc.stdout}
    try:
        return {"ok": True, "result": json.loads(proc.stdout)}
    except json.JSONDecodeError:
        return {"ok": True, "raw": proc.stdout}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: upload.py PATH", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(upload_file(Path(sys.argv[1])), indent=2))