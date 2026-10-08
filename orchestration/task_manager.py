"""Task manager: dependency checks, scheduling, status updates."""
from __future__ import annotations
from orchestration.state import Task


def from_dicts(dicts: list[dict]) -> list[Task]:
    return [_coerce(d) for d in dicts]


def _coerce(d: dict) -> Task:
    return Task(
        task_id=str(d.get("task_id", "")),
        description=str(d.get("description", "")),
        task_type=str(d.get("task_type", "research")),
        assigned_agent=str(d.get("assigned_agent", "researcher")),
        status=str(d.get("status", "pending")),
        dependencies=list(d.get("dependencies", []) or []),
        result=str(d.get("result", "") or ""),
        retry_count=int(d.get("retry_count", 0) or 0),
        tools_needed=list(d.get("tools_needed", []) or []),
    )


def ready_tasks(tasks: list[Task], results: dict) -> list[Task]:
    """Tasks whose dependencies are all completed."""
    done = {t.task_id for t in tasks if t.status == "completed"}
    done |= {k for k, v in results.items() if v}
    out = []
    for t in tasks:
        if t.status != "pending":
            continue
        if all(d in done for d in (t.dependencies or [])):
            out.append(t)
    return out


def context_for(task: Task, results: dict) -> str:
    """Relevant previous results (dependency outputs) for agent context."""
    parts = []
    for d in (task.dependencies or []):
        if d in results and results[d]:
            parts.append(f"[{d}]:\n{str(results[d])[:1500]}")
    return "\n\n".join(parts)
