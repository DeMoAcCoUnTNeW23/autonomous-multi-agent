"""LangGraph representation of the workflow (understandable, not over-built).

START -> PLAN -> EXECUTE -> VERIFY -> {PASS -> REPORT -> END | FAIL -> REPLAN -> EXECUTE}
"""
from __future__ import annotations
from typing import TypedDict


class GraphState(TypedDict, total=False):
    objective: str
    tasks_total: int
    tasks_done: int
    verified: bool
    replans: int


def build_graph():
    """Build the state machine. Falls back to a trivial shim if langgraph missing."""
    try:
        from langgraph.graph import StateGraph, START, END

        g = StateGraph(GraphState)

        def plan_node(s: GraphState):
            return {"tasks_total": s.get("tasks_total", 0)}

        def execute_node(s: GraphState):
            return {"tasks_done": s.get("tasks_done", 0)}

        def verify_node(s: GraphState):
            return {"verified": s.get("verified", False)}

        def report_node(s: GraphState):
            return {}

        def replan_node(s: GraphState):
            return {"replans": s.get("replans", 0) + 1, "verified": False}

        g.add_node("plan", plan_node)
        g.add_node("execute", execute_node)
        g.add_node("verify", verify_node)
        g.add_node("report", report_node)
        g.add_node("replan", replan_node)
        g.add_edge(START, "plan")
        g.add_edge("plan", "execute")
        g.add_edge("execute", "verify")

        def route(s: GraphState):
            if s.get("verified"):
                return "report"
            if s.get("replans", 0) >= 1:
                return "report"  # avoid infinite replan: report with limitations
            return "replan"

        g.add_conditional_edges("verify", route, {"report": "report", "replan": "replan"})
        g.add_edge("replan", "execute")
        g.add_edge("report", END)
        return g.compile()
    except Exception:
        # Minimal shim with same .invoke interface
        class _Shim:
            def invoke(self, s):
                return s
        return _Shim()
