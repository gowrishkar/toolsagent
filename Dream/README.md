# DREAM

**D**iary audit · **R**eplay/reflect (Submind) · **E**volve procedures · **A**rchive · **M**aintenance (`hermes update`)

Nightly **script-only** pipeline (no LLM). State: `~/.hermes/dream/`. Reports: `~/.hermes/dream/reports/`.

## Run

```bash
python3 ~/toolsagent/Dream/run_dream.py
python3 ~/toolsagent/Dream/run_dream.py --dry-run   # no hermes update, no Drive upload
```

## Cron (recommended)

`30 0 * * *` IST — after `build-log` (`0 0`). Hermes job: `dream-nightly`, `no_agent`, script `run_dream.py`.

## Phases

1. `diary_audit` — ensure diary section for log day
2. `replay_reflect` — diary Errors → Submind `reflect --failed`; Actions → success reflect
3. `hermes update -y --no-backup`
4. `backup` — tarball `~/.hermes` (excludes secrets/large DBs)
5. `upload` — `.tar.gz` → Google Drive **Archive** folder (`knowledge-drive.json`)

Drive upload uses `google-workspace` skill `google_api.py drive upload`.