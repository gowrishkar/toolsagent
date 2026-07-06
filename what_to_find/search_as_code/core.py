"""HTTP fetch, HTML parsing, and shared utilities."""

from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36 SearchAsCode/1.0"
)


def fetch(url: str, timeout: int = 15, user_agent: str = USER_AGENT) -> Tuple[int, str, str]:
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        if requests:
            r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            return r.status_code, r.url, r.text[:1_000_000]
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - profile-controlled URLs
            body = resp.read(1_000_000).decode("utf-8", "ignore")
            return resp.status, resp.geturl(), body
    except Exception as e:
        return 0, url, f"FETCH_ERROR: {type(e).__name__}: {e}"


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[Tuple[str, str]] = []
        self._href: Optional[str] = None
        self._buf: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            d = dict(attrs)
            self._href = d.get("href")
            self._buf = []

    def handle_data(self, data):
        if self._href is not None:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href:
            text = " ".join("".join(self._buf).split())
            self.links.append((self._href, text))
            self._href = None
            self._buf = []


def clean_text(s: str) -> str:
    s = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def title_of(html_text: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.I | re.S)
    return clean_text(m.group(1))[:180] if m else ""


def canonical_url(url: str, keep_query_hosts: Optional[List[str]] = None) -> str:
    keep_query_hosts = keep_query_hosts or []
    p = urllib.parse.urlsplit(url)
    query = p.query if any(h in p.netloc.lower() for h in keep_query_hosts) else ""
    return urllib.parse.urlunsplit(
        (p.scheme, p.netloc.lower().replace("www.", ""), p.path.rstrip("/"), query, "")
    )


def host_in_url(url: str, hosts: List[str]) -> bool:
    u = url.lower()
    return any(h in u for h in hosts)


def extract_jsonld_by_type(body: str, types: List[str]) -> List[dict]:
    want = set(types)
    jobs: List[dict] = []
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        body,
        flags=re.I | re.S,
    ):
        raw = html.unescape(m.group(1)).strip()
        try:
            import json

            data = json.loads(raw)
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                typ = x.get("@type") or x.get("type")
                if isinstance(typ, list):
                    match = any(t in want for t in typ)
                else:
                    match = typ in want
                if match:
                    jobs.append(x)
                for v in x.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(x, list):
                stack.extend(x)
    return jobs


def search_duckduckgo(
    query: str,
    max_results: int,
    allow_hosts: List[str],
    extra_hosts: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    extra_hosts = extra_hosts or []
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    status, _final, body = fetch(url, timeout=20)
    if status != 200:
        return []
    parser = LinkExtractor()
    parser.feed(body)
    out: List[Dict[str, str]] = []
    for href, text in parser.links:
        if not href:
            continue
        real = href
        if "uddg=" in href:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            if qs.get("uddg"):
                real = qs["uddg"][0]
        if real.startswith("//"):
            real = "https:" + real
        if not real.startswith("http"):
            continue
        if any(domain in real for domain in ["duckduckgo.com", "bing.com/yhp"]):
            continue
        if not host_in_url(real, allow_hosts) and not host_in_url(real, extra_hosts):
            continue
        out.append({"url": real, "title": text[:200], "query": query, "search_status": str(status)})
        if len(out) >= max_results:
            break
    return out