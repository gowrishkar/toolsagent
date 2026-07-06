"""Load YAML/JSON search profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

DEFAULT_ATS = [
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "myworkdayjobs.com",
    "workdayjobs.com",
    "smartrecruiters.com",
    "workable.com",
]


def _load_text(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML required for .yaml profiles: pip install pyyaml")
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Profile must be a mapping: {path}")
    return data


def load_profile(path: str | Path) -> Dict[str, Any]:
    p = Path(path).expanduser().resolve()
    data = _load_text(p)
    data.setdefault("schema", "sac.profile.v1")
    data.setdefault("allowlist", [])
    data.setdefault("trusted_hosts", data.get("ats_hints", DEFAULT_ATS))
    data.setdefault("discovery", {})
    disc = data["discovery"]
    disc.setdefault("site_queries", {})
    disc.setdefault("role_queries", [])
    disc.setdefault("seed_pages", [])
    disc.setdefault("use_remoteok_api", False)
    disc.setdefault("duckduckgo_role_query_limit", 8)
    data.setdefault("patterns", {"positive": {}, "hard_reject": {}})
    data.setdefault("target_title_regex", "")
    data.setdefault("jsonld_types", ["JobPosting"])
    data.setdefault("scoring", {})
    sc = data["scoring"]
    sc.setdefault("min_shortlist_score", 8.0)
    sc.setdefault("min_positive_signals", 2)
    sc.setdefault("max_output", 10)
    data.setdefault("output_schema", "search_as_code.v1")
    data.setdefault("quality_first", True)
    data["_profile_path"] = str(p)
    data["_profile_name"] = p.stem
    return data


def profiles_dir() -> Path:
    # toolsagent/profiles (repo root)
    return Path(__file__).resolve().parents[2] / "profiles"