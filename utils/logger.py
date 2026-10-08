"""Simple workflow logging with agent prefixes."""
from datetime import datetime

PREFIXES = {
    "PLANNER": "[PLANNER]",
    "RESEARCHER": "[RESEARCHER]",
    "ANALYST": "[ANALYST]",
    "EXECUTOR": "[EXECUTOR]",
    "VERIFIER": "[VERIFIER]",
    "REPORTER": "[REPORTER]",
    "TOOL": "[TOOL]",
    "ORCHESTRATOR": "[ORCHESTRATOR]",
    "WORKFLOW": "[WORKFLOW]",
}


def log(agent: str, message: str):
    prefix = PREFIXES.get(agent.upper(), f"[{agent.upper()}]")
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} {prefix} {message}", flush=True)
