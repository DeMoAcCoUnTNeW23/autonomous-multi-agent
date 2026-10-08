"""Tavily web-search tool: Internet discovery layer.

Returns structured results (never a raw API dump):
[{"title", "url", "content", "score"}]

Requires TAVILY_API_KEY. Raises RuntimeError when unconfigured/failing
so the researcher can retry, then fall back and report the limitation
instead of fabricating results.
"""
from __future__ import annotations
from config.settings import settings, has_tavily
from utils.logger import log


def search_web(query: str, max_results: int = 5) -> list[dict]:
    query = (query or "").strip()
    if not query:
        return []
    if not has_tavily():
        raise RuntimeError(
            "Tavily is not configured (TAVILY_API_KEY missing). "
            "Add it to .env to enable Internet research."
        )
    # Never print the key — only use it for the client.
    resp = None
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        resp = client.search(
            query=query,
            max_results=max(1, min(max_results, settings.max_web_results)),
            include_answer=False,
            search_depth="advanced",
        )
    except ImportError:
        # Package missing — use the REST API directly (same results).
        log("TOOL", "tavily-python missing, using Tavily REST API")
        import requests
        try:
            r = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": settings.tavily_api_key,
                      "query": query,
                      "max_results": max(1, min(max_results, settings.max_web_results)),
                      "search_depth": "advanced",
                      "include_answer": False},
                timeout=30,
            )
            if r.status_code in (401, 403):
                raise RuntimeError("Tavily rejected the API key (401/403). Check TAVILY_API_KEY.")
            r.raise_for_status()
            resp = r.json()
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Tavily search failed: {e}")
    except Exception as e:
        raise RuntimeError(f"Tavily search failed: {e}")
    if resp is None:
        raise RuntimeError("Tavily search failed: empty response")

    structured = []
    for r in (resp.get("results") or []):
        structured.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),   # Tavily snippet/content
            "score": r.get("score"),           # relevance score if provided
        })
    log("TOOL", f"tavily search: '{query[:60]}' -> {len(structured)} results")
    return structured
