"""Centralized configuration. All agents use this — never hard-code keys/models elsewhere.

The user never selects a model: OPENROUTER_MODEL is optional, and when it is
blank (or the configured model fails) the system automatically resolves a
working model via OpenRouter and falls back as needed.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

# Load .env from the project root explicitly (works regardless of CWD),
# and let it override any stale process environment values.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env", override=True)
except Exception:
    pass


def _clean(value: str | None) -> str:
    """Strip whitespace/quotes users often paste around keys in .env."""
    v = (value or "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1].strip()
    return v


# Static fallback only used when the live model list is unreachable.
AUTO_MODEL_CANDIDATES = [
    "google/gemini-2.0-flash-exp:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]

# Tried first during auto-resolution: known decent free models (verified live).
PREFERRED_AUTO_MODELS = [
    "poolside/laguna-s-2.1:free",
    "nvidia/nemotron-3.5-lightning:free",
]

_MODEL_ERROR_HINTS = ("not found", "no endpoints", "404", "invalid model",
                      "model_not_found", "does not exist")


@dataclass
class Settings:
    openrouter_api_key: str = field(default_factory=lambda: _clean(os.getenv("OPENROUTER_API_KEY")))
    openrouter_model: str = field(default_factory=lambda: _clean(os.getenv("OPENROUTER_MODEL")))
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    max_research_iterations: int = int(os.getenv("MAX_RESEARCH_ITERATIONS", "3") or 3)
    max_retries: int = int(os.getenv("MAX_RETRIES", "2") or 2)
    request_timeout: int = 60
    # --- Internet research (Tavily + BeautifulSoup) ---
    tavily_api_key: str = field(default_factory=lambda: _clean(os.getenv("TAVILY_API_KEY")))
    max_web_results: int = int(os.getenv("MAX_WEB_RESULTS", "10") or 10)
    max_sources: int = int(os.getenv("MAX_SOURCES", "5") or 5)
    max_content_chars: int = int(os.getenv("MAX_CONTENT_CHARS", "12000") or 12000)
    web_request_timeout: int = int(os.getenv("WEB_REQUEST_TIMEOUT", "15") or 15)


settings = Settings()

# Session cache: once a model is proven to respond, keep using it.
_resolved_model: str | None = None


def has_api_key() -> bool:
    return bool(settings.openrouter_api_key)


def has_tavily() -> bool:
    """True when Internet research is configured. Never logs/prints the key."""
    return bool(settings.tavily_api_key)


def _is_model_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(h in msg for h in _MODEL_ERROR_HINTS)


def _probe_model(model: str) -> bool:
    """Return True if OpenRouter serves this model (HTTP 200 + a completion choice).

    Deliberately loose: free-tier models often return blank tiny samples but
    generate fine on real prompts. Availability (not sample content) is the signal;
    real calls have their own retry/fallback.
    """
    import requests
    try:
        r = requests.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={"model": model,
                  "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
                  "max_tokens": 10},
            timeout=45,
        )
        if r.status_code != 200:
            return False
        return bool((r.json().get("choices") or []))
    except Exception:
        return False


def _live_free_models(limit: int = 8) -> list[str]:
    """Free models straight from OpenRouter's live catalogue (no auth needed)."""
    import requests
    try:
        r = requests.get(f"{settings.openrouter_base_url}/models", timeout=20)
        if r.status_code != 200:
            return []
        ids = [m.get("id", "") for m in r.json().get("data", [])]
        return [i for i in ids if i.endswith(":free")][:limit]
    except Exception:
        return []


def resolve_model() -> str:
    """Decide which model to use — automatically, no user selection needed.

    1. Configured OPENROUTER_MODEL is verified with a live probe; a dead
       model (404 / no endpoints) is skipped, never blindly trusted.
    2. Otherwise the first live free model that probes OK is used.
    3. The winner is cached for the whole session.
    """
    global _resolved_model
    if _resolved_model:
        return _resolved_model
    if settings.openrouter_model:
        try:
            if _probe_model(settings.openrouter_model):
                _resolved_model = settings.openrouter_model
                return _resolved_model
        except Exception:
            pass
    candidates = PREFERRED_AUTO_MODELS + [c for c in _live_free_models()
                                           if c not in PREFERRED_AUTO_MODELS]
    candidates = candidates or list(AUTO_MODEL_CANDIDATES)
    for candidate in candidates:
        try:
            if _probe_model(candidate):
                _resolved_model = candidate
                return _resolved_model
        except Exception:
            continue
    _resolved_model = candidates[0]
    return _resolved_model


def _fallback_after(failed_model: str) -> str | None:
    """Pick the next live candidate after a model failure; None if exhausted."""
    global _resolved_model
    tried = ([settings.openrouter_model] if settings.openrouter_model else [])
    tried += PREFERRED_AUTO_MODELS + [c for c in (_live_free_models() or AUTO_MODEL_CANDIDATES)
                                      if c not in tried]
    try:
        nxt = tried[tried.index(failed_model) + 1]
    except (ValueError, IndexError):
        return None
    _resolved_model = nxt
    return nxt


def get_llm(model: str | None = None):
    """Return a LangChain ChatOpenAI pointed at OpenRouter, or None if no key.

    Centralized: every agent calls this. No UI/agent code picks models —
    the model resolves automatically via resolve_model().
    """
    if not has_api_key():
        return None
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or resolve_model(),
            openai_api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout=settings.request_timeout,
            default_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "Autonomous Multi-Agent System",
            },
        )
    except Exception:
        return None


def invoke_llm(llm, system: str, user: str, max_tokens: int = 2000) -> str:
    """Invoke LLM; on model-availability errors auto-switch models and retry."""
    from langchain_core.messages import SystemMessage, HumanMessage
    msgs = [SystemMessage(content=system), HumanMessage(content=user)]
    try:
        llm.max_tokens = max_tokens  # bound output length (faster, cheaper)
    except Exception:
        pass
    attempts = len(AUTO_MODEL_CANDIDATES) + 1
    last: Exception | None = None
    for _ in range(attempts):
        try:
            resp = llm.invoke(msgs)
            text = getattr(resp, "content", str(resp)) or ""
            return text.strip()
        except Exception as e:
            last = e
            if not _is_model_error(e):
                raise
            current = getattr(getattr(llm, "model_name", None), "", None) or getattr(llm, "model", "")
            current = str(current)
            nxt = _fallback_after(current) if current else None
            if not nxt:
                raise
            llm = get_llm(nxt)
            if llm is None:
                raise last
    raise last or RuntimeError("LLM invocation failed")


def diagnose() -> dict:
    """Safe connectivity report (keys redacted) for main.py / app.py / debugging."""
    info: dict = {
        "env_file": str(_PROJECT_ROOT / ".env"),
        "env_file_exists": (_PROJECT_ROOT / ".env").exists(),
        "openrouter_key": bool(settings.openrouter_api_key),
        "tavily_key": bool(settings.tavily_api_key),
        "configured_model": settings.openrouter_model or "(auto)",
        "openrouter_reachable": False,
        "active_model": None,
        "error": None,
    }
    if not info["openrouter_key"]:
        info["error"] = "OPENROUTER_API_KEY missing — put it in .env (see .env.example)."
        return info
    try:
        model = resolve_model()
        if _probe_model(model):
            info["openrouter_reachable"] = True
            info["active_model"] = model
        else:
            info["error"] = f"OpenRouter did not answer with '{model}'."
    except Exception as e:
        info["error"] = f"OpenRouter probe failed: {e}"
    return info
