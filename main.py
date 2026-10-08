"""CLI entry point: python main.py"""
from config.settings import settings, has_api_key, has_tavily
from orchestration.orchestrator import Orchestrator
from reporting.report_formatter import save_report
from examples.example_tasks import EXAMPLES


def print_progress(stage: str, detail: str = ""):
    print(f"  [{stage.upper()}] {detail}")


def show_monitor(state, phase: str = ""):
    print("\n" + "=" * 60)
    print("AUTONOMOUS AI WORKFLOW")
    print("=" * 60)
    print(f"Objective: {state.user_objective[:100]}")
    print(f"Workflow Status: {state.workflow_status.upper()} {phase}")
    for t in state.plan:
        icon = {"completed": "✓", "running": "●", "failed": "✕"}.get(t.status, "○")
        print(f"{icon} {t.task_id} [{t.assigned_agent}] {t.description[:70]} — {t.status.upper()}")
    print(f"Retries: {state.retry_count}")
    print("=" * 60 + "\n")


def main():
    print("=" * 60)
    print("AUTONOMOUS MULTI-AGENT AI SYSTEM")
    print("=" * 60)
    if has_api_key():
        print(f"Model: OpenRouter / {settings.openrouter_model or '(auto — system picks a working model)'}")
    else:
        print("No OPENROUTER_API_KEY found — running in heuristic fallback mode.")
        print("Add it to .env for full LLM-powered research.")
    if has_tavily():
        print("Tavily: connected — Internet research enabled.")
    else:
        print("Tavily: not configured — web research unavailable (add TAVILY_API_KEY to .env).")
    if has_api_key():
        print("Checking OpenRouter connection...")
        from config.settings import diagnose
        d = diagnose()
        if d.get("openrouter_reachable"):
            print(f"OpenRouter: OK — active model: {d.get('active_model')}")
        else:
            print(f"OpenRouter: PROBLEM — {d.get('error') or 'unreachable'}")
    print("Type 'exit' to quit, 'examples' to see sample objectives.\n")

    while True:
        try:
            obj = input("Enter your objective:\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not obj:
            continue
        if obj.lower() in ("exit", "quit"):
            print("Goodbye.")
            break
        if obj.lower() == "examples":
            for i, e in enumerate(EXAMPLES, 1):
                print(f"\n--- Example {i}: {e['title']} ---\n{e['objective']}")
            print()
            continue

        orch = Orchestrator(progress_callback=print_progress)
        try:
            state = orch.run(obj)
        except Exception as e:
            print(f"\n⚠ Workflow Error: {e}\n")
            continue
        show_monitor(state, "COMPLETED")
        print(state.report)
        path = save_report(state.report)
        print(f"\nReport saved to: {path}")
        v = state.verification or {}
        print("\n" + "=" * 60)
        print("WORKFLOW COMPLETED")
        print("=" * 60)
        done = len([t for t in state.plan if t.status == "completed"])
        failed = len([t for t in state.plan if t.status == "failed"])
        print(f"Tasks Completed: {done}\nTasks Failed: {failed}\nRetries: {state.retry_count}")
        print(f"Verification: {'PASSED' if v.get('verified') else 'NEEDS REVIEW'}")
        print("Report: GENERATED")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
