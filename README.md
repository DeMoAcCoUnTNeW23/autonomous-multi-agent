# Autonomous Multi-Agent AI Research, Workflow & Task Automation System

A **local-first, general-purpose autonomous workflow engine**. You enter any complex
objective; the system plans, researches, analyzes, verifies, and produces a
**professional structured report** — not raw agent chatter.

## Project Overview

Single Python project, in-memory state, OpenRouter as the LLM provider. Two
frontends (CLI + Streamlit) share the same backend (`orchestration/` + `agents/` + `tools/`).

User objective → Planner → Dynamic task graph → Orchestrator → Researcher /
Analyst / Executor (controlled tools) → Shared context → Verifier →
PASS: Reporter → Professional report / FAIL: retry + replan.

## Architecture

```
Streamlit (app.py) / CLI (main.py)
        → Orchestrator (orchestration/orchestrator.py, workflow.py, task_manager.py, state.py)
        → Planner / Researcher / Analyst / Executor / Verifier / Reporter (agents/)
        → Tool layer with permission checks (tools/tool_registry.py)
        → Shared WorkflowState (in-memory) → Report (reporting/)
```

## Agents

| Agent | File | Role |
|---|---|---|
| Planner | `agents/planner.py` | Breaks objective into tasks, assigns agents, sets dependencies/tools |
| Researcher | `agents/researcher.py` | Iterative deep-research loop with follow-up queries |
| Analyst | `agents/analyst.py` | Patterns, comparisons, implications, conclusions |
| Executor | `agents/executor.py` | Python computation / file / API actions (only when planned) |
| Verifier | `agents/verifier.py` | Completeness, accuracy, consistency, evidence; returns `{verified, score, issues, recommendation}` |
| Reporter | `agents/reporter.py` | Verified state → adaptive Markdown report |

## Workflow

1. Objective → `Orchestrator.run()` → Planner builds dynamic task graph.
2. Tasks run respecting dependencies; each agent gets prior-task context.
3. Failures: classified → retried up to `MAX_RETRIES=2` → else marked failed.
4. Verifier checks; on FAIL the orchestrator replans once (extra research task) and re-verifies.
5. Reporter generates the final Markdown report (shown + saved to `reports/`).

## Deep Research

`agents/researcher.py`: search → inspect → extract → identify gaps → follow-up
queries → search again (up to `MAX_RESEARCH_ITERATIONS`) → synthesize. Sources
`{title, url, finding}` preserved; no fabricated citations — offline mode is labeled.

## Internet Research

The application can retrieve current information from the web. Internet is a
**capability, not a mandatory stage**: the planner decides per objective
whether current information is needed (`agents/planner.py: needs_internet()`).

Research pipeline:

```text
User Objective
 ↓
Planner (needs Internet? yes/no)
 ↓
Tavily Search (dynamic queries from the task, never hard-coded)
 ↓
Select Sources (relevance-ranked, de-duplicated, max MAX_SOURCES)
 ↓
BeautifulSoup (fetch + extract page content, max MAX_CONTENT_CHARS)
 ↓
Research Agent (source-tied findings with confidence + contradictions)
 ↓
Analysis → Verification (cited URLs cross-checked) → Report
```

If a page can't be extracted (JS/bot protection/paywall), the Tavily snippet
is used as fallback evidence and the workflow continues. If Tavily is missing
or fails, the system says so explicitly — it never pretends old LLM knowledge
is current.

## Tavily Setup

```env
TAVILY_API_KEY=your_key
```

Get a key at https://tavily.com, put it in `.env` (never commit `.env`;
only placeholders live in `.env.example`). Optional tuning in `.env`:

```env
MAX_RESEARCH_ITERATIONS=3
MAX_WEB_RESULTS=10
MAX_SOURCES=5
MAX_CONTENT_CHARS=12000
WEB_REQUEST_TIMEOUT=15
```

The Streamlit sidebar shows Tavily/OpenRouter status (config check only, no
API call), and results render an Internet Research panel plus per-source
extraction status.

## Tool Calling

Capabilities (not mandatory steps): `web_search` (Tavily-first, legacy fallback),
`web_fetch`, `web_extract`, `web_retrieval` (legacy), `python`,
`file_reader`, `api`. Permissions in `tools/tool_registry.py`:

```python
TOOL_PERMISSIONS = {"researcher": ["web_search","web_fetch","web_extract",...], "executor": ["python","file_reader","api"], ...}
```

Every call goes through permission check → execute / reject.

## Verification

`agents/verifier.py` returns structured JSON (`verified/score/issues/missing_items/recommendation`).
UI shows a verification panel; FAIL triggers autonomous replan.

## Retry / Replanning

Task fail → retry (max 2) → still failing → continue with error recorded.
Verification fail → planner creates additional research task → re-execute → re-verify.

## Report Generation

`agents/reporter.py` adapts sections to the objective (default: Executive Summary,
Objective, Approach, Findings, Analysis, Recommendations, Limitations,
Conclusion, Sources, Verification). The LLM always structures the report;
a static template is only a last-resort fallback. Reports are always in
English unless the objective explicitly requests another language
(e.g. "...write the report in Urdu"). Rendered in terminal and Streamlit; downloadable `.md`.

## Installation (Windows)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Setup

```bash
copy .env.example .env
```

Edit `.env`:

```env
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

Without a key the system runs in **heuristic fallback mode** (still demonstrates
planning → research → analysis → verification → report). With a key, all agents
use OpenRouter via the centralized `config/settings.py` (`get_llm()`).

## Running

CLI:
```bash
python main.py
```

Streamlit UI (AI Intelligence Command Center):
```bash
streamlit run app.py
```

The UI is presentation-only (`app.py` + `ui/`): hero + telemetry, mission
objective deck, agent pipeline timeline, agent cards, Internet intelligence
panel, source explorer, activity console, verification panel, and the final
intelligence report with download. Backend calls are unchanged.

## Example Requests

- `Research the current state of AI agents, identify major trends, analyze their applications, and prepare a detailed report.`
- `Compare several AI development frameworks, evaluate strengths and weaknesses, and recommend one for a student project.`
- `Investigate how generative AI is changing software engineering, research major impacts, identify risks and opportunities, compare perspectives, provide recommendations, and create a detailed professional report.`
- See `examples/example_tasks.py` (also in the Streamlit dropdown).

## Project Structure

```
main.py  app.py  config/  agents/  orchestration/  tools/  tools/web/  reporting/  ui/  utils/  examples/  reports/
```

`tools/web/`: `tavily_search.py` (Internet discovery) · `page_fetcher.py`
(HTML retrieval) · `content_extractor.py` (BeautifulSoup → clean text) ·
`models.py` (`WebSource` evidence model).

## Limitations (v1)

In-memory state only (no persistence), local sequential execution (no
parallelism), no auth/scheduling. Internet research notes: some websites
cannot be extracted (JavaScript, bot protection, paywalls — snippet fallback
is used instead); search results depend on the provider; Tavily usage consumes
API credits; current information should always be verified against the cited
sources.

## Future Improvements

Persistent memory, database, web interface polish, parallel execution, more
tools (PDF, arXiv), auth, scheduled workflows, deployment, evaluation harness.
