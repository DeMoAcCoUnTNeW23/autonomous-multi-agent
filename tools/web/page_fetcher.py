"""Webpage fetcher: retrieves raw HTML only (no parsing here).

Respects timeouts, uses a clear User-Agent, handles errors gracefully,
and never attempts to bypass authentication/paywalls/bot protection.
"""
from __future__ import annotations
import requests
from config.settings import settings

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AutonomousResearch/1.0; +http://localhost)"}


def fetch_page(url: str, timeout: int | None = None) -> str:
    """Fetch HTML for a publicly accessible page. Raises on failure."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Refusing to fetch non-HTTP URL: {url!r}")
    timeout = timeout or settings.web_request_timeout
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Fetch timed out after {timeout}s: {url}")
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        raise RuntimeError(f"HTTP {status} fetching {url} (may need JS/login/paywall — skipping)")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Connection error fetching {url}: {e}")
    html = resp.text or ""
    if not html.strip():
        raise RuntimeError(f"Empty response from {url}")
    return html
