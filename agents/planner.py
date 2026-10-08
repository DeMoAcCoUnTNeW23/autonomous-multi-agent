"""Planner agent: converts a high-level objective into a dynamic task graph.

The planner decides what work is needed, which agent does each task,
which tools are required, and task dependencies. Never a fixed workflow.
"""
from __future__ import annotations
import json
import re
from config.settings import get_llm, invoke_llm
from utils.logger import log

VALID_AGENTS = {"researcher", "analyst", "executor", "verifier", "reporter"}
VALID_TYPES = {"research", "analysis", "execution", "verification", "reporting"}

# Heuristic signals that the objective needs current Internet information.
INTERNET_KEYWORDS = (
    "latest", "current", "recent", "news", "today", "this week", "2025", "2026",
    "trend", "ecosystem", "compare", "comparison", "versus", " vs ", "review",
    "best", "top ", "market", "industry", "release", "update", "development",
)


def needs_internet(objective: str) -> bool:
    """Decide dynamically whether the objective needs current web information.

    Conceptual/stable knowledge ("Explain what an LLM is") -> False.
    Time-sensitive or evidence-hungry goals ("latest developments...") -> True.
    Internet is a capability, not a mandatory stage.
    """
    obj = (objective or "").lower()
    heuristic = any(k in obj for k in INTERNET_KEYWORDS)
    llm = get_llm()
    if llm is None:
        return heuristic
    try:
        raw = invoke_llm(
            llm,
            "Does answering the user's objective require current information from the "
            "Internet (recent events, latest versions, market data, comparisons of "
            "existing tools)? Answer with exactly one word: YES or NO.",
            f"Objective: {objective}",
        ).strip().upper()
        if "YES" in raw[:10]:
            return True
        if "NO" in raw[:10]:
            return False
    except Exception as e:
        log("PLANNER", f"Internet-need check failed ({e}) — heuristic fallback.")
    return heuristic


def _heuristic_plan(objective: str) -> list[dict]:
    """Fallback when no LLM key is configured. Keyword-driven, still dynamic."""
    obj = objective.lower()
    tasks, i = [], 1

    def add(desc, ttype, agent, deps=None, needs_tools=None):
        nonlocal i
        tasks.append({
            "task_id": f"T{i}", "description": desc, "task_type": ttype,
            "assigned_agent": agent, "status": "pending",
            "dependencies": deps or [], "result": "",
            "retry_count": 0, "tools_needed": needs_tools or [],
        })
        i += 1
        return f"T{i-1}"

    t1 = add(f"Research background and key facts for: {objective}", "research", "researcher",
             needs_tools=["web_search", "web_fetch", "web_extract"])
    deps = [t1]
    if any(k in obj for k in ("compar", "vs", "versus", "framework", "option", "best", "recommend")):
        t2 = add("Compare approaches/options, evaluate strengths and weaknesses", "research", "researcher",
                 deps=deps, needs_tools=["web_search", "web_fetch", "web_extract"])
        deps = [t2]
    if any(k in obj for k in ("dataset", "data", "csv", "file", "analy", "trend", "metric", "comput", "calculat")):
        t2 = add("Examine local data/files and run quantitative analysis", "execution", "executor",
                 deps=deps, needs_tools=["python", "file_reader"])
        deps = [t2]
    t3 = add("Synthesize evidence into patterns, implications and conclusions", "analysis", "analyst", deps=deps)
    tasks.append({
        "task_id": f"T{i}", "description": "Verify completeness, accuracy and consistency of findings",
        "task_type": "verification", "assigned_agent": "verifier", "status": "pending",
        "dependencies": [t3], "result": "", "retry_count": 0, "tools_needed": [],
    })
    return tasks


def create_plan(objective: str) -> list[dict]:
    """Build a dynamic task graph for the objective. Uses LLM, falls back to heuristics."""
    log("PLANNER", "Creating task plan...")
    llm = get_llm()
    if llm is None:
        log("PLANNER", "No API key — using heuristic planner.")
        return _heuristic_plan(objective)

    system = (
        "You are a Planner agent in a multi-agent system. Break the user's objective "
        "into 4-7 concrete subtasks. Return ONLY valid JSON: a list of objects with keys "
        "description, task_type (research|analysis|execution|verification), "
        "assigned_agent (researcher|analyst|executor|verifier), dependencies (list of 0-based "
        "indexes of earlier tasks), tools_needed (subset of web_search, web_fetch, web_extract, python, file_reader, api). "
        "Include research tasks when external facts are needed, execution only when computation/files/APIs "
        "are needed, always include one analysis and leave verification to the system (do NOT add verification task)."
    )
    try:
        raw = invoke_llm(llm, system, f"Objective: {objective}")
        m = re.search(r"\[.*\]", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        tasks = []
        for idx, t in enumerate(data[:7]):
            agent = str(t.get("assigned_agent", "researcher")).lower()
            ttype = str(t.get("task_type", "research")).lower()
            if agent not in VALID_AGENTS:
                agent = "researcher"
            if ttype not in VALID_TYPES:
                ttype = "research"
            dep_idx = t.get("dependencies", []) or []
            deps = [f"T{d+1}" for d in dep_idx if isinstance(d, int) and 0 <= d < idx]
            if not deps and idx > 0:
                deps = [f"T{idx}"]  # default chain to previous task
            tasks.append({
                "task_id": f"T{idx+1}", "description": str(t.get("description", ""))[:300],
                "task_type": ttype, "assigned_agent": agent, "status": "pending",
                "dependencies": deps, "result": "", "retry_count": 0,
                "tools_needed": t.get("tools_needed", []),
            })
        if not tasks:
            raise ValueError("empty plan")
        log("PLANNER", f"Plan created with {len(tasks)} tasks.")
        return tasks
    except Exception as e:
        log("PLANNER", f"LLM planning failed ({e}) — using heuristic planner.")
        return _heuristic_plan(objective)
