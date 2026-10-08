"""Orchestrator: central controller. Owns state, routes tasks to agents.

1. Receive objective -> 2. Init state -> 3. Planner -> 4. Schedule tasks ->
5. Route to agents with context -> 6. Collect results -> 7. Failures/retries ->
8. Replanning on failed verification -> 9. Report generation.
"""
from __future__ import annotations
from config.settings import settings
from orchestration.state import WorkflowState
from orchestration import task_manager
from orchestration.workflow import build_graph
from agents import planner as _planner
from agents import researcher as _researcher
from agents import analyst as _analyst
from agents import executor as _executor
from agents import verifier as _verifier
from agents import reporter as _reporter
from utils.logger import log


class Orchestrator:
    def __init__(self, progress_callback=None):
        self.progress = progress_callback  # fn(stage:str, detail:str) for UI
        self.graph = build_graph()

    def _emit(self, stage: str, detail: str = ""):
        if self.progress:
            try:
                self.progress(stage, detail)
            except Exception:
                pass

    def _run_single_task(self, state: WorkflowState, task) -> str:
        """Route one task to its agent and return result text (may raise)."""
        ctx = task_manager.context_for(task, state.task_results)
        role = task.assigned_agent.lower()
        if role == "researcher":
            out = _researcher.run_research(task.description, context=ctx,
                                           use_internet=state.internet_required,
                                           language=state.language)
            for s in out.get("sources", []):
                if s.get("url") and s["url"] not in {x.get("url") for x in state.sources}:
                    state.sources.append(s)
            state.research_findings.append(out["findings"])
            # Aggregate Internet stats across research tasks for the UI.
            ws = out.get("web_stats", {}) or {}
            for k in ("iterations", "found", "selected", "extracted", "fallbacks"):
                state.web_stats[k] = state.web_stats.get(k, 0) + ws.get(k, 0)
            if out.get("internet_used"):
                state.internet_used = True
            return out["findings"]
        if role == "analyst":
            res = _analyst.run_analysis(state.user_objective, state.research_findings,
                                        state.execution_outputs, language=state.language)
            state.analysis = res
            return res
        if role == "executor":
            res = _executor.run_execution(task.description, context=ctx or "\n".join(state.research_findings)[:2000])
            state.execution_outputs.append(res)
            return res
        # verifier/reporter tasks handled at workflow level; run generically
        return f"Task {task.task_id} acknowledged ({role})."

    def run(self, objective: str) -> WorkflowState:
        state = WorkflowState(user_objective=objective.strip(), workflow_status="running")
        if not state.user_objective:
            raise ValueError("Objective must not be empty.")
        log("ORCHESTRATOR", f"Starting workflow for: {objective[:100]}...")
        state.note("Workflow started")
        # Report language: always English unless the user asked otherwise.
        from utils.helpers import detect_report_language
        state.language = detect_report_language(objective)
        log("ORCHESTRATOR", f"Report language: {state.language}")
        state.note(f"Report language: {state.language}")
        self._emit("planning", "Planner is decomposing the objective...")

        # PLAN (+ decide whether the objective needs current Internet info)
        state.internet_required = _planner.needs_internet(objective)
        log("ORCHESTRATOR",
            f"Internet research {'required' if state.internet_required else 'not required'} "
            "for this objective.")
        state.note(f"Internet required: {state.internet_required}")
        self._emit("planning",
                   f"Internet {'needed — Tavily research enabled' if state.internet_required else 'not needed — LLM knowledge suffices'}")
        plan_dicts = _planner.create_plan(objective)
        state.plan = task_manager.from_dicts(plan_dicts)
        state.note(f"Plan created: {len(state.plan)} tasks")
        self._emit("planned", f"{len(state.plan)} tasks created")

        # EXECUTE TASKS (respect dependencies, sequential v1)
        self._emit("research", "Executing tasks...")
        guard = 0
        while True:
            guard += 1
            if guard > 50:
                state.errors.append("Scheduling guard tripped.")
                break
            ready = task_manager.ready_tasks(state.plan, state.task_results)
            if not ready:
                break
            for task in ready:
                task.status = "running"
                self._emit(task.assigned_agent, f"{task.task_id}: {task.description[:90]}")
                log("ORCHESTRATOR", f"Routing {task.task_id} -> {task.assigned_agent}")
                try:
                    result = self._run_single_task(state, task)
                    task.result = result
                    task.status = "completed"
                    state.task_results[task.task_id] = result
                    state.completed_tasks.append(task.task_id)
                    state.note(f"{task.task_id} completed by {task.assigned_agent}")
                except Exception as e:
                    task.retry_count += 1
                    state.retry_count += 1
                    if task.retry_count <= settings.max_retries:
                        task.status = "pending"
                        msg = f"{task.task_id} failed (attempt {task.retry_count}) — retrying: {e}"
                        state.note(msg); state.events.append(f"RETRY: {msg}")
                        self._emit("retry", msg)
                        log("ORCHESTRATOR", msg)
                    else:
                        task.status = "failed"
                        task.result = f"FAILED after {task.retry_count} attempts: {e}"
                        state.task_results[task.task_id] = task.result
                        state.errors.append(task.result)
                        state.note(task.result)
            # loop again: newly unblocked tasks become ready

        # If analyst never ran (planner omitted it), synthesize now
        if not state.analysis and state.research_findings:
            self._emit("analysis", "Synthesizing findings...")
            state.analysis = _analyst.run_analysis(objective, state.research_findings,
                                                   state.execution_outputs,
                                                   language=state.language)

        # VERIFY
        self._emit("verification", "Verifier is checking completeness...")
        done = len([t for t in state.plan if t.status == "completed"])
        total = len(state.plan)
        combined = "\n\n".join(state.research_findings)
        state.verification = _verifier.verify(objective, combined, state.analysis,
                                              state.sources, done, total)
        try:
            self.graph.invoke({"objective": objective, "tasks_total": total,
                               "tasks_done": done,
                               "verified": state.verification.get("verified", False),
                               "replans": 0})
        except Exception:
            pass

        # REPLAN once if verification failed
        if not state.verification.get("verified") and state.replan_count < 1:
            missing = state.verification.get("missing_items", []) or ["Additional research required"]
            log("ORCHESTRATOR", f"Verification failed — replanning: {missing}")
            state.note(f"Replanning: {missing}")
            self._emit("replan", f"Verifier requested more work: {missing[0] if missing else ''}")
            state.replan_count += 1
            extra_desc = f"Follow-up research to address gaps: {'; '.join(missing[:2])}. Original objective: {objective}"
            from orchestration.state import Task as _T
            extra = _T(task_id=f"T{len(state.plan)+1}", description=extra_desc,
                       task_type="research", assigned_agent="researcher",
                       status="completed" if False else "pending", dependencies=[],
                       tools_needed=["web_search"])
            state.plan.append(extra)
            try:
                result = self._run_single_task(state, extra)
                extra.result = result; extra.status = "completed"
                state.task_results[extra.task_id] = result
                state.completed_tasks.append(extra.task_id)
                state.analysis = _analyst.run_analysis(objective, state.research_findings,
                                                       state.execution_outputs,
                                                       language=state.language)
                done = len([t for t in state.plan if t.status == "completed"])
                state.verification = _verifier.verify(objective, "\n\n".join(state.research_findings),
                                                      state.analysis, state.sources, done, len(state.plan))
            except Exception as e:
                state.errors.append(f"Replan task failed: {e}")

        # REPORT
        self._emit("reporting", "Reporter is writing the final report...")
        exec_text = "\n\n".join(state.execution_outputs)
        ws = state.web_stats or {}
        if state.internet_used:
            method_note = (
                "The planner flagged this objective as needing current web information. "
                f"The researcher ran {ws.get('iterations', 0)} Tavily search iteration(s), "
                f"discovered {ws.get('found', 0)} results, selected {ws.get('selected', 0)} "
                f"sources, extracted full page content from {ws.get('extracted', 0)} page(s) "
                f"with BeautifulSoup ({ws.get('fallbacks', 0)} fell back to search snippets). "
                "Findings below cite only retrieved sources.")
        elif state.internet_required:
            method_note = ("The planner flagged this objective as needing current web information, "
                           "but Tavily is not configured (TAVILY_API_KEY missing) or unreachable, "
                           "so the workflow fell back to legacy search/LLM knowledge. "
                           "Current-information claims should be treated as unverified.")
        else:
            method_note = ("The planner judged that no current web information was required, "
                           "so the answer was produced from model knowledge and workflow context.")
        state.report = _reporter.generate_report(objective, "\n\n".join(state.research_findings),
                                                 state.analysis, exec_text,
                                                 state.sources, state.verification,
                                                 method_note, language=state.language)
        state.workflow_status = "completed"
        state.note("Report generated — workflow completed")
        self._emit("completed", "Workflow completed")
        log("ORCHESTRATOR", "Workflow completed.")
        return state
