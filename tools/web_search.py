"""Web search + page retrieval tools. Free/local-friendly, no key required.

Uses `ddgs` (duckduckgo-search) if installed, otherwise falls back to
DuckDuckGo lite HTML scraping, otherwise returns honest mock results
(clearly marked) so the workflow still runs offline.
"""
from __future__ import annotations
import re
import html as _html

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (AutonomousResearch/1.0)"}


def web_search(query: str, max_results: int = 5) -> list[dict]:
    query = (query or "").strip()
    if not query:
        return []
    # 1) Try ddgs package
    try:
        from ddgs import DDGS
        out = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                out.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "source": "duckduckgo",
                })
        if out:
            return out
    except Exception:
        pass
    # 2) Try lite HTML endpoint
    try:
        resp = requests.post(
            "https://lite.duckduckgo.com/lite/",
            data={"q": query},
            headers=HEADERS,
            timeout=15,
        )
        if resp.ok:
            links = re.findall(
                r'<a rel="nofollow" href="([^"]+)"[^>]*>(.*?)</a>', resp.text, re.S
            )
            results = []
            for url, title in links[:max_results]:
                title = _html.unescape(re.sub(r"<.*?>", "", title)).strip()
                if url.startswith("//"):
                    url = "https:" + url
                results.append({"title": title, "url": url, "snippet": "", "source": "duckduckgo-lite"})
            if results:
                return results
    except Exception:
        pass
    # 3) Offline fallback — clearly marked, never fabricated as real citations
    return [{
        "title": f"No live results (offline) for: {query}",
        "url": "",
        "snippet": "Web search unavailable. Findings below are LLM background knowledge — treat as unverified.",
        "source": "offline-fallback",
    }]


def web_retrieve(url: str, max_chars: int = 6000) -> str:
    """Fetch a page and return plain text (truncated)."""
    if not url:
        return ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if not resp.ok:
            return f"Could not retrieve {url} (HTTP {resp.status_code})."
        text = re.sub(r"<script.*?</script>", " ", resp.text, flags=re.S | re.I)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<.*?>", " ", text, flags=re.S)
        text = _html.unescape(re.sub(r"\s+", " ", text)).strip()
        return text[:max_chars]
    except Exception as e:
        return f"Could not retrieve {url}: {e}"
