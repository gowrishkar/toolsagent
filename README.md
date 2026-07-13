# ToolsAgent

One repo for how autonomous agents **behave** and **find** things.

| Pillar | Folder | Origin |
|--------|--------|--------|
| **How to behave** | `how_to_behave/` | Submind — completion contracts, anti–fake-done, subconscious habits |
| **What to find** | `what_to_find/search_as_code/` | Search as Code — YAML profiles, discover → validate → rank → JSON |
| **DREAM (nightly)** | `Dream/` | Diary audit, reflect, `hermes update`, backup, Drive upload (scripts only) |
| **ANT Loop (coding)** | `skills/ant-loop/` | Autonomous /spec → /build → /review → Merge loop (self-contained: bundles `backend-developer` + `code-review-and-quality`) |
| **Backend playbook** | `skills/backend-developer/` | `/build` rails — REST, auth, SQL/NoSQL, caching, deploy |
| **Code review gate** | `skills/code-review-and-quality/` | `/review` multi-axis gate — correctness, security, perf, readability |

Designed for **Hermes Agent** (and any Python agent loop).

## Hermes wiring (default profile)

State lives in `~/.hermes/toolsagent/`:

- `active_contract.json` — current task done-checks + evidence
- `subconscious_memory.json` + `subconscious_procedures.md` — soft habits from successful runs

Scripts:

- `~/.hermes/scripts/toolsagent_sac_hawks.sh` — job scout pipeline
- `toolsagent/hermes/behave_gate.py` — **must pass** before claiming “done” on build/fix tasks
- `toolsagent/hermes/reflect_run.py` — optional post-run reflection

Load skill: **`toolsagent`** (`skill_view toolsagent`).

## Behave: finish gate

```bash
python3 ~/toolsagent/hermes/behave_gate.py create \
  --goal "Ship feature X" \
  --checks "tests pass,artifact exists,user verified"

python3 ~/toolsagent/hermes/behave_gate.py evidence --check "tests pass" --output "9 passed"
python3 ~/toolsagent/hermes/behave_gate.py finish --message "Done, all tests pass"
```

Exit code **2** = not allowed to report complete (missing evidence or lazy flags).

## Find: search pipeline

```bash
export PYTHONPATH=~/toolsagent/what_to_find
python3 -m search_as_code --profile ~/toolsagent/profiles/generic_web.yaml --pretty
```

## Tests

```bash
cd ~/toolsagent
pip install -r requirements.txt pytest
PYTHONPATH=how_to_behave:what_to_find pytest -q
```

## ANT Loop (autonomous coding)

`skills/ant-loop/` is the orchestration layer: a self-driving coding loop where
the **only human steps** are `/spec` (describe a feature) and 🚀 approve.

```
/spec ──▶ /build ⇄ /review ──▶ Merge (🚀)
          └───────────┘  (review loops back to build on blocking issues)
```

- **`/spec`** — writes a tracked issue (spec, acceptance, edge cases, tech).
- **`/build`** — cron `build-monitor` polls `spec-ready` issues, spawns a
  `delegate_task` subagent to implement (follows `backend-developer` playbook).
- **`/review`** — cron `review-monitor` tests, opens a PR, deploys a preview,
  notifies; waits for 🚀 before merging.
- **Board** — GitHub Issues (default) or a local Markdown file
  (`board.example.md` ships as the template).
- **Daily improvement** — a cron patches `ant-loop` + `backend-developer`
  with lessons from the day's runs.

**Dependencies (bundled):** the loop delegates to two sibling skills that
**ship in this repo** — `backend-developer` (build rails) and
`code-review-and-quality` (review gate). Load all three together:
`skill_view ant-loop`, `skill_view backend-developer`, `skill_view code-review-and-quality`.
The branded flow diagram is `skills/ant-loop/references/loop.jpg`.

## License

MIT — Gowrishkar.