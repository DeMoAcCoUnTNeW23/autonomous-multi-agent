"""BeautifulSoup content extractor: HTML -> clean LLM-ready text.

Removes script/style/noscript/nav boilerplate, normalizes whitespace,
de-duplicates repeated lines, and enforces MAX_CONTENT_CHARS.
"""
from __future__ import annotations
import re
from config.settings import settings


def extract_text(html: str, max_chars: int | None = None) -> str:
    if not html or not html.strip():
        return ""
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise RuntimeError(f"beautifulsoup4 is not installed: {e}")
    max_chars = max_chars or settings.max_content_chars

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.body or soup
    text = main.get_text(separator="\n") if main else ""
    # Normalize: strip lines, drop empties, de-duplicate repeats
    seen, lines = set(), []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) < 20 or line in seen:
            continue
        seen.add(line)
        lines.append(line)
    clean = "\n".join(lines).strip()
    if len(clean) > max_chars:
        clean = clean[:max_chars] + "\n...[content truncated]"
    return clean
