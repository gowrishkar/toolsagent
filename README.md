# ToolsAgent

One repo for how autonomous agents **behave** and **find** things.

| Pillar | Folder | Origin |
|--------|--------|--------|
| **How to behave** | `how_to_behave/` | Submind — completion contracts, anti–fake-done, subconscious habits |
| **What to find** | `what_to_find/search_as_code/` | Search as Code — YAML profiles, discover → validate → rank → JSON |
| **DREAM (nightly)** | `Dream/` | Diary audit, reflect, `hermes update`, backup, Drive upload (scripts only) |

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

## License

MIT — Gowrishkar.