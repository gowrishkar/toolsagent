#!/usr/bin/env python3
"""Create compressed tarball of ~/.hermes (secrets and heavy DBs excluded)."""
from __future__ import annotations

import json
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
HERMES = Path.home() / ".hermes"
OUT_DIR = HERMES / "dream" / "backups"

EXCLUDE_NAMES = {
    ".env",
    "google_token.json",
    "google_client_secret.json",
    "auth.json",
    ".git-credentials",
}

EXCLUDE_GLOBS = [
    "sessions/*",
    "profiles/*/sessions/*",
    "hermes-agent/.git/*",
    "audio_cache/*",
    "image_cache/*",
    "video_cache/*",
    "__pycache__/*",
    "*.pyc",
]


def _filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
    name = tarinfo.name
    parts = Path(name).parts
    if any(p in EXCLUDE_NAMES for p in parts):
        return None
    if name.endswith("state.db") or name.endswith("sessions.db"):
        return None
    for pat in EXCLUDE_GLOBS:
        if Path(name).match(pat) or name.replace("\\", "/").find(pat.replace("*", "")) >= 0:
            # simple glob: skip paths containing pattern base
            if "sessions/" in name.replace("\\", "/") and "profiles/" in name:
                return None
    return tarinfo


def create_backup(stamp: str | None = None) -> Path:
    stamp = stamp or datetime.now(IST).strftime("%Y-%m-%d")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUT_DIR / f"hermes-backup-{stamp}"
    tar_path = base.with_suffix(".tar.gz")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(HERMES, arcname="hermes", filter=_filter)
    return tar_path


def hermes_update(skip: bool = False) -> dict:
    if skip:
        return {"skipped": True}
    cmd = ["hermes", "update", "-y", "--no-backup"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return {
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-500:],
        "stderr_tail": (proc.stderr or "")[-500:],
    }


if __name__ == "__main__":
    p = create_backup()
    print(json.dumps({"path": str(p), "size": p.stat().st_size}, indent=2))