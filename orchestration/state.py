"""Shared in-memory workflow state. No database — exists only while running."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Task:
    task_id: str
    description: str
    task_type: str = "research"          # research|analysis|execution|verification|reporting
    assigned_agent: str = "researcher"   # researcher|analyst|executor|verifier|reporter
    status: str = "pending"              # pending|running|completed|failed
    dependencies: list = field(default_factory=list)
    result: str = ""
    retry_count: int = 0
    tools_needed: list = field(default_factory=list)


@dataclass
class WorkflowState:
    user_objective: str = ""
    plan: list = field(default_factory=list)          # List[Task]
    completed_tasks: list = field(default_factory=list)
    task_results: dict = field(default_factory=dict)  # task_id -> result text
    research_findings: list = field(default_factory=list)
    sources: list = field(default_factory=list)       # [{title,url,finding}]
    analysis: str = ""
    execution_outputs: list = field(default_factory=list)
    verification: dict = field(default_factory=dict)
    report: str = ""
    errors: list = field(default_factory=list)
    retry_count: int = 0
    replan_count: int = 0
    workflow_status: str = "idle"  # idle|running|completed|failed
    events: list = field(default_factory=list)  # human-readable event log for UI
    # --- Internet research tracking (capability, not mandatory stage) ---
    internet_required: bool = False  # planner decision: does objective need the web?
    internet_used: bool = False      # did any research task actually use Tavily?
    web_stats: dict = field(default_factory=dict)  # {iterations,found,selected,extracted,fallbacks}
    # --- Report language: English unless the user explicitly requests otherwise ---
    language: str = "English"

    def note(self, msg: str):
        self.events.append(msg)
