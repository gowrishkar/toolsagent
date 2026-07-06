#!/usr/bin/env python3
"""Hermes CLI: discipline contract + finish gate (Submind)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HERMES_STATE = Path.home() / ".hermes" / "toolsagent"
CONTRACT_PATH = HERMES_STATE / "active_contract.json"

sys.path.insert(0, str(REPO / "how_to_behave"))
from agent_discipline import AgentDisciplineLayer  # noqa: E402


def _load_contract(layer: AgentDisciplineLayer):
    if not CONTRACT_PATH.exists():
        raise SystemExit(f"No contract at {CONTRACT_PATH}. Run: create")
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    c = layer.create_contract(goal=data["goal"], done_checks=data["done_checks"])
    for check, items in data.get("evidence", {}).items():
        for item in items:
            layer.add_evidence(
                c,
                check,
                status=item.get("status", "passed"),
                output=item.get("output", ""),
                path=item.get("path"),
                note=item.get("note", ""),
            )
    return c


def _save_contract(contract) -> None:
    HERMES_STATE.mkdir(parents=True, exist_ok=True)
    out = {
        "goal": contract.goal,
        "done_checks": contract.done_checks,
        "evidence": {
            k: [
                {
                    "status": e.status,
                    "output": e.output,
                    "path": e.path,
                    "note": e.note,
                }
                for e in v
            ]
            for k, v in contract.evidence.items()
        },
    }
    CONTRACT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")


def cmd_create(args) -> int:
    layer = AgentDisciplineLayer()
    checks = [c.strip() for c in args.checks.split(",") if c.strip()]
    contract = layer.create_contract(goal=args.goal, done_checks=checks)
    _save_contract(contract)
    print(json.dumps({"ok": True, "goal": contract.goal, "done_checks": checks}))
    return 0


def cmd_evidence(args) -> int:
    layer = AgentDisciplineLayer()
    contract = _load_contract(layer)
    layer.add_evidence(
        contract,
        args.check,
        status=args.status,
        output=args.output or "",
        path=args.path,
        note=args.note or "",
    )
    _save_contract(contract)
    print(json.dumps({"ok": True, "check": args.check}))
    return 0


def cmd_finish(args) -> int:
    layer = AgentDisciplineLayer()
    contract = _load_contract(layer)
    result = layer.can_finish(
        contract,
        final_message=args.message or "",
        tool_calls_made=not args.no_tools,
    )
    payload = {
        "allowed": result.allowed,
        "missing": result.missing,
        "failed": result.failed,
        "lazy_flags": result.lazy_flags,
        "report": result.report,
        "next_action": layer.next_action(contract),
    }
    print(json.dumps(payload, indent=2))
    return 0 if result.allowed else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ToolsAgent behave gate for Hermes")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="Start completion contract for current task")
    c.add_argument("--goal", required=True)
    c.add_argument("--checks", required=True, help="Comma-separated done checks")
    c.set_defaults(func=cmd_create)

    e = sub.add_parser("evidence", help="Attach proof for a done check")
    e.add_argument("--check", required=True)
    e.add_argument("--output", default="")
    e.add_argument("--path", default=None)
    e.add_argument("--status", default="passed")
    e.add_argument("--note", default="")
    e.set_defaults(func=cmd_evidence)

    f = sub.add_parser("finish", help="Gate before telling user task is done")
    f.add_argument("--message", default="", help="Draft final user message")
    f.add_argument("--no-tools", action="store_true", help="Claim no tool calls were made")
    f.set_defaults(func=cmd_finish)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())