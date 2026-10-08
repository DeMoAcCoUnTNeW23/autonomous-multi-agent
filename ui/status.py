"""Derive display statuses from the existing workflow state.

No backend logic here — pure mapping of WorkflowState -> UI labels.
Statuses: done | running | idle | warn | fail | skip
"""
from html import escape

STAGE_ORDER = ["planner", "researcher", "analyst", "executor", "verifier", "reporter"]
STAGE_LABELS = {
    "planner": "PLANNER",
    "researcher": "RESEARCHER",
    "analyst": "ANALYST",
    "executor": "EXECUTOR",
    "verifier": "VERIFIER",
    "reporter": "REPORTER",
}

GLYPH = {"done": "✓", "running": "●", "idle": "○",
         "warn": "⚠", "fail": "✕", "skip": "–"}
WORD = {"done": "COMPLETED", "running": "RUNNING", "idle": "PENDING",
        "warn": "ATTENTION", "fail": "FAILED", "skip": "STANDBY"}


def stage_statuses(state, running: bool = False) -> dict:
    """Map each agent stage to a status key."""
    if state is None:
        return {s: ("running" if running and s == "planner" else "idle")
                for s in STAGE_ORDER}
    out = {}
    tasks = list(getattr(state, "plan", []) or [])

    def agent_state(role: str):
        mine = [t for t in tasks if t.assigned_agent.lower() == role]
        if not mine:
            return None
        if any(t.status == "failed" for t in mine):
            return "fail"
        if all(t.status == "completed" for t in mine):
            return "done"
        if any(t.status == "running" for t in mine):
            return "running"
        return "idle"

    out["planner"] = "done" if tasks else "idle"
    out["researcher"] = agent_state("researcher") or "idle"
    out["analyst"] = agent_state("analyst") or (
        "done" if getattr(state, "analysis", "") else "idle")
    ex = agent_state("executor")
    out["executor"] = ex if ex else (
        "done" if getattr(state, "execution_outputs", []) else "skip")
    v = (getattr(state, "verification", {}) or {})
    if v:
        out["verifier"] = "done" if v.get("verified") else "warn"
    else:
        out["verifier"] = "idle"
    out["reporter"] = "done" if getattr(state, "report", "") else "idle"

    if running and getattr(state, "workflow_status", "") != "completed":
        for s in STAGE_ORDER:  # highlight first unfinished stage as live
            if out[s] == "idle":
                out[s] = "running"
                break
    return out


def op_note(state, role: str) -> str:
    """One-line operational note per agent (never chain-of-thought)."""
    if state is None:
        return "Standby — awaiting objective."
    notes = {
        "planner": f"Task plan created: {len(getattr(state, 'plan', []))} tasks."
                   if getattr(state, "plan", []) else "Standby.",
        "researcher": _research_note(state),
        "analyst": "Evidence synthesized." if getattr(state, "analysis", "")
                   else "Waiting for research.",
        "executor": (f"{len(getattr(state, 'execution_outputs', []))} action(s) executed."
                     if getattr(state, "execution_outputs", [])
                     else "No execution required for this objective."),
        "verifier": _verify_note(state),
        "reporter": "Report generated." if getattr(state, "report", "")
                    else "Waiting for verification.",
    }
    return notes.get(role, "")


def _research_note(state) -> str:
    ws = getattr(state, "web_stats", {}) or {}
    if getattr(state, "internet_used", False):
        return (f"{ws.get('found', 0)} found → {ws.get('selected', 0)} selected → "
                f"{ws.get('extracted', 0)} extracted.")
    if getattr(state, "research_findings", []):
        return f"{len(state.research_findings)} finding block(s) collected."
    return "Researching sources." if getattr(state, "plan", []) else "Standby."


def _verify_note(state) -> str:
    v = (getattr(state, "verification", {}) or {})
    if not v:
        return "Waiting."
    return (f"Score {v.get('score', 'n/a')} — "
            f"{'PASSED' if v.get('verified') else 'NEEDS WORK'}")


def esc(value) -> str:
    return escape("" if value is None else str(value))
