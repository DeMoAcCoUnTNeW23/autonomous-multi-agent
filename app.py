"""Streamlit UI — PRESENTATION LAYER ONLY (AI Intelligence Command Center).

All intelligence lives in orchestration/ + agents/ + tools/.
This file is the UI controller: it calls `Orchestrator.run(objective)`
and delegates every visual to ui/components.py + ui/styles.py.

Run: streamlit run app.py
"""
import streamlit as st

from orchestration.orchestrator import Orchestrator
from ui.components import (
    apply_example,
    example_labels,
    render_agent_cards,
    render_console,
    render_hero,
    render_internet,
    render_report_header,
    render_sidebar,
    render_sources,
    render_telemetry,
    render_timeline,
    render_topbar,
    render_verification,
)
from ui.styles import inject_styles

st.set_page_config(page_title="Autonomous Intelligence", page_icon="◉", layout="wide")
inject_styles()

# ---- session state (UI only; orchestrator owns workflow state) ----
for k, v in {"objective": "", "workflow_result": None, "running": False}.items():
    if k not in st.session_state:
        st.session_state[k] = v

render_sidebar()
render_topbar("SYSTEM ONLINE")

state = st.session_state.get("workflow_result")
running = bool(st.session_state.get("running"))
status_word = ("COMPLETE" if state is not None and state.workflow_status == "completed"
               else ("RUNNING" if running else "READY"))
render_hero(status_word)
render_telemetry(state, running)

# ---- objective deck ----
st.markdown('<div class="hud-panel active">'
            '<div class="hud-title">◉ MISSION OBJECTIVE</div>'
            '<div class="hud-dim">What should the autonomous intelligence system investigate?</div>'
            "</div>",
            unsafe_allow_html=True)
choice = st.selectbox("Mission profile", example_labels())
apply_example(choice)
objective = st.text_area(
    "Objective input",
    value=st.session_state["objective"],
    height=140,
    placeholder=("> Example:\n\nResearch the current state of AI agents, identify major "
                 "frameworks and trends, analyze their strengths and limitations, "
                 "and prepare a detailed recommendation report."),
    label_visibility="collapsed",
)
st.session_state["objective"] = objective

col_a, col_b = st.columns([3, 1])
with col_a:
    start = st.button("▶ INITIALIZE RESEARCH", type="primary", use_container_width=True)
with col_b:
    reset = st.button("↻ RESET", use_container_width=True)
if reset:
    st.session_state["workflow_result"] = None
    st.session_state["running"] = False
    st.rerun()

# ---- execution (same backend call as before) ----
if start:
    if not (objective or "").strip():
        st.error("Please enter an objective first.")
    else:
        st.session_state["running"] = True
        status_box = st.status("Autonomous workflow running...", expanded=True)
        progress = st.progress(0)
        stage_labels = st.empty()

        def cb(stage: str, detail: str = ""):
            key = stage.lower()
            idx = {"planning": 0, "planned": 0, "research": 1, "researcher": 1,
                   "analysis": 2, "analyst": 2, "execution": 3, "executor": 3,
                   "verification": 4, "verifier": 4, "replan": 4, "retry": 3,
                   "reporting": 5, "reporter": 5, "completed": 6}.get(key, 0)
            progress.progress(min(idx / 6, 1.0))
            stage_labels.write(f"**Current:** {stage} — {detail}")
            status_box.write(f"✓ {stage} — {detail}"[:200])

        try:
            orch = Orchestrator(progress_callback=cb)
            state = orch.run(objective.strip())
            st.session_state["workflow_result"] = state
            status_box.update(label="Workflow completed", state="complete", expanded=False)
            progress.progress(1.0)
        except Exception as e:
            status_box.update(label="Workflow error", state="error", expanded=True)
            st.error("⚠ Workflow Error — the workflow could not be completed.")
            st.write(f"Reason: {e}")
            st.write("Suggested action: Try again or modify the objective.")
            with st.expander("▼ Technical Details"):
                st.exception(e)
        finally:
            st.session_state["running"] = False
            st.rerun()

state = st.session_state.get("workflow_result")
running = bool(st.session_state.get("running"))

# ---- results ----
if state is not None:
    done = len([t for t in state.plan if t.status == "completed"])
    total = len(state.plan)
    st.markdown(
        '<div class="hud-panel active"><div class="hud-title">◉ INVESTIGATION COMPLETE</div>'
        f'<div class="hud-dim">✓ Research &nbsp;&nbsp; ✓ Analysis &nbsp;&nbsp; '
        f'✓ Verification &nbsp;&nbsp; ✓ Report Generated'
        f' &nbsp;&nbsp;— {done}/{total} tasks completed.</div></div>',
        unsafe_allow_html=True)
    render_telemetry(state, running)

    left, right = st.columns([1, 1])
    with left:
        render_timeline(state, running)
    with right:
        render_console(state)
    render_agent_cards(state, running)

    mid_l, mid_r = st.columns([1, 1])
    with mid_l:
        render_internet(state)
    with mid_r:
        render_verification(state)

    render_sources(state)

    # Final report — the centerpiece (backend Markdown, themed container).
    render_report_header(state)
    with st.container(border=True):
        st.markdown(state.report or "(empty report)")
    act_l, act_r = st.columns([3, 1])
    with act_l:
        st.download_button("⬇ DOWNLOAD REPORT", data=state.report or "",
                           file_name="research_report.md", mime="text/markdown",
                           use_container_width=True)
    with act_r:
        if st.button("↻ NEW INVESTIGATION", use_container_width=True):
            st.session_state["workflow_result"] = None
            st.session_state["running"] = False
            st.rerun()

    v = state.verification or {}
    st.markdown('<div class="hud-label">[ WORKFLOW SUMMARY ]</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tasks", len(state.plan))
    m2.metric("Retries", state.retry_count)
    m3.metric("Sources", len(state.sources))
    m4.metric("Verification", "PASSED" if v.get("verified") else "REVIEW")
else:
    st.markdown(
        '<div class="hud-panel"><div class="hud-title">◉ SYSTEM STANDBY</div>'
        '<div class="hud-dim">SYSTEM READY &nbsp;&nbsp;•&nbsp;&nbsp; AGENTS STANDBY<br>'
        'Enter an objective above and press INITIALIZE RESEARCH.<br>'
        'Your objective becomes verified knowledge.</div></div>',
        unsafe_allow_html=True)
