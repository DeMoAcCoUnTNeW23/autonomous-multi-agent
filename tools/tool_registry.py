"""Controlled tool registry: agents only get tools they are allowed to use.

Before executing a tool: Agent -> Permission Check -> Allowed? Execute : Reject
"""
from utils.logger import log
from config.settings import has_tavily
from tools import web_search as _ws
from tools import file_tools as _ft
from tools import python_tools as _pt
from tools.web import tavily_search as _tavily
from tools.web import page_fetcher as _fetcher
from tools.web import content_extractor as _extractor

TOOL_PERMISSIONS = {
    "researcher": ["web_search", "web_fetch", "web_extract", "web_retrieval"],
    "analyst": ["web_search", "python"],
    "executor": ["python", "file_reader", "api"],
    "verifier": ["web_search", "web_fetch", "web_extract", "web_retrieval",
                 "python", "file_reader"],
    "planner": [],
    "reporter": [],
}


def is_allowed(agent_role: str, tool_name: str) -> bool:
    return tool_name in TOOL_PERMISSIONS.get(agent_role.lower(), [])


def execute_tool(agent_role: str, tool_name: str, **kwargs):
    """Check permission then dispatch. Returns tool output or rejection string."""
    role = agent_role.lower()
    if not is_allowed(role, tool_name):
        msg = f"Tool '{tool_name}' NOT permitted for agent '{role}'. Denied."
        log("TOOL", msg)
        return f"PERMISSION DENIED: {msg}"
    log("TOOL", f"{tool_name} executed by {role} args={list(kwargs.keys())}")
    try:
        if tool_name == "web_search":
            # Tavily is the primary Internet provider; legacy free search is
            # the fallback when Tavily is unconfigured or fails.
            if has_tavily():
                try:
                    return _tavily.search_web(kwargs.get("query", ""),
                                              kwargs.get("max_results", 5))
                except Exception as e:
                    log("TOOL", f"Tavily failed, falling back to legacy search: {e}")
                    return _ws.web_search(kwargs.get("query", ""),
                                          kwargs.get("max_results", 5))
            return _ws.web_search(kwargs.get("query", ""), kwargs.get("max_results", 5))
        if tool_name == "web_retrieval":
            return _ws.web_retrieve(kwargs.get("url", ""))
        if tool_name == "web_fetch":
            # Fetch + extract a page. Returns dict with status; on failure
            # the caller falls back to the Tavily snippet (never a crash).
            url = kwargs.get("url", "")
            try:
                html = _fetcher.fetch_page(url)
                text = _extractor.extract_text(html)
                if not text:
                    raise RuntimeError("extractor returned empty text")
                return {"url": url, "text": text, "status": "extracted", "error": ""}
            except Exception as e:
                return {"url": url, "text": "", "status": "failed", "error": str(e)}
        if tool_name == "web_extract":
            return _extractor.extract_text(kwargs.get("html", ""))
        if tool_name == "python":
            return _pt.run_python(kwargs.get("code", ""))
        if tool_name == "file_reader":
            action = kwargs.get("action", "read")
            if action == "list":
                return _ft.list_files(kwargs.get("path", "."))
            return _ft.read_file(kwargs.get("path", ""))
        if tool_name == "api":
            import requests
            url = kwargs.get("url", "")
            r = requests.get(url, timeout=15)
            return r.text[:4000]
        return f"Unknown tool: {tool_name}"
    except Exception as e:
        return f"Tool '{tool_name}' failed: {e}"
