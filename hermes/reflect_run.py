#!/usr/bin/env python3
"""Record successful Hermes trajectory into Submind subconscious store."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HERMES_STATE = Path.home() / ".hermes" / "toolsagent"

sys.path.insert(0, str(REPO / "how_to_behave"))
from subconscious_layer import SubconsciousLayer  # noqa: E402


async def run(trajectory_path: Path, success: bool) -> None:
    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    layer = SubconsciousLayer(
        store_path=HERMES_STATE / "subconscious_memory.json",
        procedural_path=HERMES_STATE / "subconscious_procedures.md",
    )
    await layer.reflect(trajectory, success=success)
    print(json.dumps(layer.prime(), indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trajectory_json", type=Path, help="JSON list of {action, result}")
    ap.add_argument("--failed", action="store_true")
    args = ap.parse_args()
    asyncio.run(run(args.trajectory_json, success=not args.failed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())