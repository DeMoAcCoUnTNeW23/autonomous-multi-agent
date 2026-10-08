"""Executor agent: handles tasks requiring real actions.

Runs Python snippets, reads files, calls APIs. Only runs when the
planner decides execution is needed — NOT a mandatory step.
"""
from __future__ import annotations
import re
from config.settings import get_llm, invoke_llm
from tools.tool_registry import execute_tool
from utils.logger import log
from utils.helpers import truncate


def run_execution(task_description: str, context: str = "") -> str:
    log("EXECUTOR", f"Executing: {task_description[:80]}...")
    llm = get_llm()
    code = None
    # If the task already contains a code block, use it directly
    m = re.search(r"```(?:python)?\s*(.*?)```", task_description, re.S | re.I)
    if m:
        code = m.group(1).strip()
    elif llm is not None:
        # Ask LLM to produce code for the computation described
        try:
            draft = invoke_llm(
                llm,
                "You are an Executor. Given the task, either output a short Python script "
                "inside a ```python block that prints the result, OR if no computation is "
                "needed, answer the task directly in plain text.",
                f"Task: {task_description}\nContext: {truncate(context, 1500)}",
            )
            m2 = re.search(r"```(?:python)?\s*(.*?)```", draft, re.S | re.I)
            if m2:
                code = m2.group(1).strip()
            else:
                log("EXECUTOR", "Execution completed (direct answer).")
                return draft
        except Exception as e:
            return f"Executor LLM step failed: {e}"
    if code:
        output = execute_tool("executor", "python", code=code)
        result = f"Executed Python code:\n```python\n{truncate(code, 1500)}\n```\n**Output:**\n```\n{truncate(str(output), 2500)}\n```"
        log("EXECUTOR", "Execution completed.")
        return result
    # No code path: try file listing / generic note
    if any(k in task_description.lower() for k in ("file", "directory", "list", "read ", ".csv", ".txt", ".md")):
        out = execute_tool("executor", "file_reader", action="list", path=".")
        return f"File inspection (no computation needed):\n{truncate(str(out), 2000)}"
    log("EXECUTOR", "Execution completed (no tool needed).")
    return f"Task noted, no computation required: {task_description}"
