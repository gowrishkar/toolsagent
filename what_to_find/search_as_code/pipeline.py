"""Discover → hydrate → filter → score → JSON (Search as Code)."""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import dataclasses
import datetime as dt
import hashlib
import json
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core import (
    LinkExtractor,
    canonical_url,
    clean_text,
    extract_jsonld_by_type,
    fetch,
    host_in_url,
    search_duckduckgo,
    title_of,
)
from .profile import load_profile, profiles_dir

STATE_ROOT = Path(__file__).resolve().parents[2] / "state"


@dataclasses.dataclass
class Item:
    url: str
    discovery_source: str
    search_query: str = ""
    title: str = ""
    subtitle: str = ""
    summary: str = ""
    fields: Dict[str, str] = dataclasses.field(default_factory=dict)
    positive_signals: List[str] = dataclasses.field(default_factory=list)
    reject_reasons: List[str] = dataclasses.field(default_factory=list)
    fit_score: float = 0.0
    action: str = "Review"
    validation_note: str = ""
    fingerprint: str = ""
    http_status: int = 0


def _state_path(profile_name: str) -> Path:
    d = STATE_ROOT / profile_name
    d.mkdir(parents=True, exist_ok=True)
    return d / "seen.json"


def _compile_patterns(patterns: Dict[str, str]) -> Dict[str, re.Pattern]:
    return {k: re.compile(v, re.I) for k, v in patterns.items()}


def source_name(url: str, allowlist: List[str], trusted: List[str]) -> str:
    u = url.lower()
    for host in allowlist + trusted:
        if host in u:
            return host
    return urllib.parse.urlparse(url).netloc.lower().replace("www.", "")


def discover_source_pages(profile: Dict[str, Any], max_leads: int) -> List[Dict[str, str]]:
    disc = profile["discovery"]
    allow = profile["allowlist"]
    trusted = profile["trusted_hosts"]
    leads: List[Dict[str, str]] = []
    seen = set()

    def add(url: str, title: str, query: str) -> None:
        if not url.startswith("http"):
            return
        if not (host_in_url(url, allow) or host_in_url(url, trusted)):
            return
        cu = canonical_url(url)
        if cu in seen:
            return
        seen.add(cu)
        leads.append({"url": url, "title": title[:200], "query": query, "search_status": "direct"})

    if disc.get("use_remoteok_api"):
        cap = max(2, min(8, max_leads // 4))
        added = 0
        status, _final, body = fetch("https://remoteok.com/api", timeout=20)
        if status == 200:
            try:
                data = json.loads(body)
                keywords = disc.get("remoteok_keywords", ["ai", "product", "remote"])
                for item in data[1:] if isinstance(data, list) else []:
                    if not isinstance(item, dict):
                        continue
                    text = " ".join(str(item.get(k, "")) for k in ["position", "company", "description", "tags"]).lower()
                    if any(k in text for k in keywords):
                        before = len(leads)
                        add(
                            item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id')}",
                            f"{item.get('company', '')} - {item.get('position', '')}",
                            "remoteok_api",
                        )
                        if len(leads) > before:
                            added += 1
                        if added >= cap:
                            break
            except Exception:
                pass

    for page in disc.get("seed_pages", []):
        if len(leads) >= max_leads:
            break
        status, final, body = fetch(page, timeout=20)
        if status < 200 or status >= 400:
            continue
        parser = LinkExtractor()
        try:
            parser.feed(body)
        except Exception:
            continue
        link_keywords = disc.get("seed_link_keywords", ["job", "career", "docs", "article", "blog", "guide"])
        content_keywords = disc.get("seed_content_keywords", [])
        page_text = clean_text(body).lower()
        for href, text in parser.links:
            low = f"{href} {text}".lower()
            if not any(k in low for k in link_keywords):
                continue
            if content_keywords and not any(re.search(k, low, re.I) for k in content_keywords):
                if not any(re.search(k, page_text, re.I) for k in content_keywords):
                    continue
            add(urllib.parse.urljoin(final, href), text or title_of(body), f"direct_seed:{page}")
            if len(leads) >= max_leads:
                return leads
    return leads


def discover(profile: Dict[str, Any], max_leads: int, per_query: int) -> List[Dict[str, str]]:
    allow = profile["allowlist"]
    trusted = profile["trusted_hosts"]
    disc = profile["discovery"]
    direct = discover_source_pages(profile, max_leads=max_leads)
    out: List[Dict[str, str]] = []
    seen = set()
    for item in direct:
        cu = canonical_url(item["url"])
        if cu not in seen:
            seen.add(cu)
            out.append(item)
            if len(out) >= max_leads:
                return out

    queries: List[str] = list(disc.get("site_queries", {}).values())
    sites_or = " OR ".join(f"site:{s}" for s in allow[:6]) if allow else ""
    limit = int(disc.get("duckduckgo_role_query_limit", 8))
    for rq in disc.get("role_queries", [])[:limit]:
        if sites_or:
            queries.append(f"({sites_or}) {rq}")
        else:
            queries.append(rq)

    with futures.ThreadPoolExecutor(max_workers=6) as ex:
        futs = [
            ex.submit(search_duckduckgo, q, per_query, allow, trusted)
            for q in queries
        ]
        for fut in futures.as_completed(futs):
            for item in fut.result():
                cu = canonical_url(item["url"])
                if cu not in seen:
                    seen.add(cu)
                    out.append(item)
                    if len(out) >= max_leads:
                        return out
    return out


def hydrate(raw: Dict[str, str], profile: Dict[str, Any]) -> Item:
    allow = profile["allowlist"]
    trusted = profile["trusted_hosts"]
    pos_p = _compile_patterns(profile["patterns"].get("positive", {}))
    rej_p = _compile_patterns(profile["patterns"].get("hard_reject", {}))
    title_re = profile.get("target_title_regex") or ""
    title_rx = re.compile(title_re, re.I) if title_re else None
    jsonld_types = profile.get("jsonld_types") or []

    c = Item(
        url=raw["url"],
        discovery_source=source_name(raw["url"], allow, trusted),
        search_query=raw.get("query", ""),
        title=raw.get("title", ""),
    )
    status, final, body = fetch(c.url)
    c.http_status = status
    c.url = final
    if status < 200 or status >= 400:
        c.reject_reasons.append(f"http_{status or 'fetch_failed'}")
        c.validation_note = "URL did not load cleanly."
        return c

    page_title = title_of(body)
    text = clean_text(body)
    lowered = text.lower()
    c.title = page_title or c.title

    if jsonld_types:
        blocks = extract_jsonld_by_type(body, jsonld_types)
        if blocks:
            j = blocks[0]
            c.subtitle = str(j.get("headline") or j.get("title") or "")[:200]
            c.summary = clean_text(str(j.get("description") or ""))[:4000] or text[:4000]
            org = j.get("hiringOrganization") or j.get("publisher") or {}
            if isinstance(org, dict):
                c.fields["organization"] = str(org.get("name") or "unknown")
            for key in ("datePosted", "validThrough", "jobLocation", "url"):
                if key in j:
                    c.fields[key] = str(j.get(key))[:500]
        else:
            c.summary = text[:4000]
    else:
        c.summary = text[:4000]

    if not c.subtitle:
        parts = re.split(r"\s+[-|@–—]\s+", c.title)
        c.subtitle = parts[0][:120] if parts else c.title[:120]
        if len(parts) > 1:
            c.fields.setdefault("organization", parts[-1][:100])

    joined = " ".join([c.title, c.subtitle, c.summary, " ".join(c.fields.values())]).lower()
    for name, pat in pos_p.items():
        if pat.search(joined):
            c.positive_signals.append(name)
    for name, pat in rej_p.items():
        if pat.search(joined):
            c.reject_reasons.append(name)

    if title_rx and not title_rx.search(f"{c.title} {c.subtitle}"):
        c.reject_reasons.append("title_mismatch")

    closed = bool(
        re.search(
            r"\b(no longer accepting|job is closed|position has been filled|expired|archived|not found|404)\b",
            lowered,
        )
    )
    if closed:
        c.reject_reasons.append("closed_or_stale")

    min_sig = int(profile["scoring"].get("min_positive_signals", 2))
    if pos_p and len(c.positive_signals) < min_sig:
        c.reject_reasons.append("weak_positive_signal")

    c.fit_score = score_item(c, profile)
    c.action = action_for_score(c.fit_score, profile)
    c.fingerprint = make_fingerprint(c)
    c.validation_note = f"HTTP {c.http_status}; signals={','.join(c.positive_signals) or 'none'}"
    return c


def score_item(c: Item, profile: Dict[str, Any]) -> float:
    signals = set(c.positive_signals)
    base = 3.0 if c.title else 1.5
    bonus = 0.4 * len(signals)
    if c.http_status == 200:
        bonus += 1.0
    if host_in_url(c.url, profile.get("trusted_hosts", [])):
        bonus += 0.8
    penalty = 0.7 * len([r for r in c.reject_reasons if r != "weak_positive_signal"])
    score = base + bonus - penalty
    weights = profile["scoring"].get("signal_weights", {})
    for sig, w in weights.items():
        if sig in signals:
            score += float(w)
    return round(max(0.0, min(10.0, score)), 1)


def action_for_score(score: float, profile: Dict[str, Any]) -> str:
    actions = profile["scoring"].get(
        "actions",
        [
            {"min": 8.7, "label": "Act now"},
            {"min": 8.0, "label": "Prioritize"},
            {"min": 7.0, "label": "Monitor"},
            {"min": 0.0, "label": "Skip"},
        ],
    )
    for row in sorted(actions, key=lambda x: -float(x["min"])):
        if score >= float(row["min"]):
            return str(row["label"])
    return "Review"


def make_fingerprint(c: Item) -> str:
    key = "|".join([c.title.lower(), c.subtitle.lower(), canonical_url(c.url)])
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def load_seen(profile_name: str) -> Dict[str, dict]:
    p = _state_path(profile_name)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_seen(profile_name: str, seen: Dict[str, dict]) -> None:
    p = _state_path(profile_name)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(seen, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)


def run_pipeline(
    profile: Dict[str, Any],
    *,
    max_output: Optional[int] = None,
    max_leads: int = 50,
    per_query: int = 4,
    include_seen: bool = False,
    session: str = "manual",
) -> dict:
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    scoring = profile["scoring"]
    max_output = max_output or int(scoring.get("max_output", 10))
    min_score = float(scoring.get("min_shortlist_score", 8.0))
    profile_name = profile.get("_profile_name", "default")

    leads = discover(profile, max_leads=max_leads, per_query=per_query)
    items: List[Item] = []
    with futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(hydrate, lead, profile) for lead in leads]
        for fut in futures.as_completed(futs):
            items.append(fut.result())

    by_fp: Dict[str, Item] = {}
    for c in items:
        fp = c.fingerprint or make_fingerprint(c)
        existing = by_fp.get(fp)
        if existing is None or c.fit_score > existing.fit_score:
            by_fp[fp] = c
    items = list(by_fp.values())

    seen = load_seen(profile_name)
    rejected_counts: Dict[str, int] = {}
    shortlisted: List[Item] = []
    for c in items:
        if not include_seen and c.fingerprint in seen:
            c.reject_reasons.append("already_seen")
        final_reject = bool(c.reject_reasons) or c.fit_score < min_score
        if final_reject:
            reasons = c.reject_reasons or ["below_score_threshold"]
            for r in sorted(set(reasons)):
                rejected_counts[r] = rejected_counts.get(r, 0) + 1
            continue
        shortlisted.append(c)

    shortlisted.sort(key=lambda x: x.fit_score, reverse=True)
    shortlisted = shortlisted[:max_output]

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    for c in shortlisted:
        seen[c.fingerprint] = {
            "seen_at": now,
            "title": c.title,
            "url": c.url,
            "fit_score": c.fit_score,
        }
    save_seen(profile_name, seen)

    source_mix: Dict[str, int] = {}
    rejected_count = 0
    for c in items:
        source_mix[c.discovery_source] = source_mix.get(c.discovery_source, 0) + 1
        if c not in shortlisted:
            rejected_count += 1

    return {
        "schema": profile.get("output_schema", "search_as_code.v1"),
        "profile": profile_name,
        "session": session,
        "started_at_utc": started,
        "finished_at_utc": now,
        "approved_sources": profile.get("allowlist", []),
        "reviewed_count": len(items),
        "raw_leads_count": len(leads),
        "validated_shortlist_count": len(shortlisted),
        "rejected_suppressed_count": rejected_count,
        "rejected_suppressed_by_reason": dict(sorted(rejected_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "source_mix_used": dict(sorted(source_mix.items())),
        "items": [dataclasses.asdict(c) for c in shortlisted],
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Search as Code — programmable retrieval pipeline")
    ap.add_argument(
        "--profile",
        default=str(profiles_dir() / "generic_web.yaml"),
        help="Path to YAML/JSON profile",
    )
    ap.add_argument("--session", default="manual")
    ap.add_argument("--max-output", type=int, default=None)
    ap.add_argument("--max-leads", type=int, default=50)
    ap.add_argument("--per-query", type=int, default=4)
    ap.add_argument("--include-seen", action="store_true")
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args(argv)

    profile = load_profile(args.profile)
    result = run_pipeline(
        profile,
        max_output=args.max_output,
        max_leads=args.max_leads,
        per_query=args.per_query,
        include_seen=args.include_seen,
        session=args.session,
    )
    print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())