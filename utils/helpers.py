"""Small helpers: timestamps, filenames, text utils."""
from datetime import datetime
import re


def timestamp_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def report_filename(prefix: str = "report") -> str:
    return f"{prefix}_{timestamp_str()}.md"


def truncate(text: str, limit: int = 4000) -> str:
    if text is None:
        return ""
    text = str(text)
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"


def slugify(text: str, limit: int = 60) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return s[:limit] or "report"


# Languages the user can explicitly request in the objective.
# Anything not matching these patterns -> English (the default).
LANGUAGE_PATTERNS = {
    "Urdu": (r"\burdu\b", r"\bardu\b"),
    "Hindi": (r"\bhindi\b",),
    "French": (r"\bfrench\b", r"\bfran[çc]ais\b"),
    "Spanish": (r"\bspanish\b", r"\bespa[nñ]ol\b"),
    "German": (r"\bgerman\b", r"\bdeutsch\b"),
    "Arabic": (r"\barabic\b",),
    "Chinese": (r"\bchinese\b", r"\bmandarin\b"),
    "Portuguese": (r"\bportuguese\b", r"\bportugu[eê]s\b"),
    "Italian": (r"\bitalian\b",),
    "Turkish": (r"\bturkish\b",),
    "Russian": (r"\brussian\b",),
    "Japanese": (r"\bjapanese\b",),
    "Korean": (r"\bkorean\b",),
    "Dutch": (r"\bdutch\b",),
}


def detect_report_language(objective: str) -> str:
    """Report language for this workflow. Always English unless the user
    explicitly asks for another language in the objective.

    Matches requests like '... in Urdu', 'write the report in Hindi',
    'en français' — not incidental words ('research in AI' stays English).
    """
    text = (objective or "").lower()
    # Explicit request cues: 'in <lang>', 'report in <lang>', 'en <lang>'...
    wants_other = bool(re.search(
        r"\b(in|en)\s+[a-zçñê]+\b|\breport\s+(in|en)\b|\bwrite\b.*\bin\b|\brespond\b|\banswer\b",
        text))
    if not wants_other:
        return "English"
    for lang, patterns in LANGUAGE_PATTERNS.items():
        if any(re.search(p, text) for p in patterns):
            return lang
    return "English"
