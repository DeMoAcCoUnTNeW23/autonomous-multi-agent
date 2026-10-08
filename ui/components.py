"""Presentation components for the AI Intelligence interface.

Every function here only READS existing state/settings and renders UI.
Backend calls stay in app.py (Orchestrator) — never duplicated here.
"""
from urllib.parse import urlparse

import streamlit as st

from config.settings import settings, has_api_key, has_tavily
from examples.example_tasks import EXAMPLES
from ui.status import (STAGE_ORDER, STAGE_LABELS, GLYPH, WORD,
                       stage_statuses, op_note, esc)


# ---------------------------------------------------------------- top bar ---
def render_topbar(sys_state: str = "SYSTEM ONLINE") -> None:
    ok = "●" if has_api_key() else "○"
    st.markdown(
        f'<div class="hud-topbar"><span class="brand">◉ AI INTELLIGENCE</span>'
        f'<span><span class="ok">{ok} {esc(sys_state)}</span>'
        f' &nbsp;&nbsp;OPENROUTER&nbsp;&nbsp;TAVILY&nbsp;&nbsp;v1.0</span></div>',
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------- hero ---
def render_hero(status_word: str = "READY") -> None:
    web = "ENABLED" if has_tavily() else "OFFLINE"
    model = esc(settings.openrouter_model or "(auto)")
    st.markdown(
        '<div class="hud-hero">'
        '<h1>AUTONOMOUS<br><span class="neon">INTELLIGENCE</span></h1>'
        '<div class="tagline">THINK&nbsp;&nbsp;•&nbsp;&nbsp;RESEARCH&nbsp;&nbsp;•&nbsp;&nbsp;VERIFY</div>'
        '<div class="sub">Turn complex objectives into verified intelligence and reports.</div>'
        '<div class="hud-rule"></div>'
        f'<div class="hud-telemetry"><span>SYSTEM <b>ONLINE</b></span>'
        f'<span>AGENTS <b>06</b></span><span>WEB ACCESS <b>{web}</b></span>'
        f'<span>MODEL <b>OPENROUTER / {model}</b></span>'
        f'<span>STATUS <b>{esc(status_word)}</b></span></div>'
        '</div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------- telemetry ---
def render_telemetry(state, running: bool = False) -> None:
    ws = (getattr(state, "web_stats", {}) or {}) if state else {}
    if state is None:
        cells = [("AGENTS", "6"), ("WEB ACCESS", "ON" if has_tavily() else "OFF"),
                 ("SOURCES", "0"), ("STATUS", "READY")]
    else:
        status = "COMPLETE" if state.workflow_status == "completed" else (
            "RUNNING" if running else "STANDBY")
        cells = [("AGENTS", "6"),
                 ("TASKS", str(len(state.plan))),
                 ("SOURCES", str(len(state.sources))),
                 ("RETRIES", str(state.retry_count)),
                 ("STATUS", status)]
        if ws.get("iterations"):
            cells.insert(3, ("ROUNDS", str(ws.get("iterations", 0))))
    html = '<div class="tele-grid">' + "".join(
        f'<div class="tele-cell"><div class="k">{k}</div><div class="v">{esc(v)}</div></div>'
        for k, v in cells) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------- timeline ---
def render_timeline(state, running: bool = False) -> None:
    st.markdown('<div class="hud-label">[ WORKFLOW 01 — AGENT PIPELINE ]</div>',
                unsafe_allow_html=True)
    statuses = stage_statuses(state, running)
    parts = ['<div class="flow">']
    for i, stage in enumerate(STAGE_ORDER):
        s = statuses[stage]
        cls = {"done": "done", "running": "run", "idle": "idle",
               "warn": "warn", "fail": "fail", "skip": "idle"}[s]
        parts.append(
            f'<div class="flow-node {cls}"><span class="name">{STAGE_LABELS[stage]}</span>'
            f'<span class="stt">{GLYPH[s]} {WORD[s]}</span></div>')
        if i < len(STAGE_ORDER) - 1:
            parts.append('<div class="flow-link">│<br>▼</div>')
    parts.append("</div>")
    st.markdown("\n".join(parts), unsafe_allow_html=True)


# -------------------------------------------------------------- agent cards --
def render_agent_cards(state, running: bool = False) -> None:
    st.markdown('<div class="hud-label">[ UNIT 02 — AGENT CARDS ]</div>',
                unsafe_allow_html=True)
    statuses = stage_statuses(state, running)
    cards = ['<div class="agent-grid">']
    for stage in STAGE_ORDER:
        s = statuses[stage]
        lit = " lit" if s in ("done", "running") else ""
        tasks_n = ""
        if state is not None and getattr(state, "plan", []):
            mine = [t for t in state.plan if t.assigned_agent.lower() == stage]
            if mine:
                tasks_n = f'<div class="row"><span>TASKS</span><b>{len(mine)}</b></div>'
        cards.append(
            f'<div class="agent-card{lit}"><div class="an">◉ {STAGE_LABELS[stage]}</div>'
            f'<div class="row"><span>STATUS</span><b>{GLYPH[s]} {WORD[s]}</b></div>'
            f'{tasks_n}<div class="note">{esc(op_note(state, stage))}</div></div>')
    cards.append("</div>")
    st.markdown("\n".join(cards), unsafe_allow_html=True)


# ---------------------------------------------------------- internet panel ---
def render_internet(state) -> None:
    ws = (getattr(state, "web_stats", {}) or {}) if state else {}
    online = has_tavily()
    dot = "● ONLINE" if online else "○ OFFLINE"
    need = ("YES" if state.internet_required else "NO") if state else "—"
    rows = [
        ("SEARCH ENGINE", f"TAVILY &nbsp; {dot}"),
        ("NEEDED FOR OBJECTIVE", need),
        ("PAGES ANALYZED", str(ws.get("extracted", 0))),
        ("SOURCES FOUND", str(ws.get("found", 0))),
        ("SOURCES USED", str(ws.get("selected", 0))),
        ("RESEARCH ROUNDS", str(ws.get("iterations", 0))),
    ]
    html = ['<div class="hud-panel"><div class="hud-title">◉ INTERNET INTELLIGENCE</div>']
    for k, v in rows:
        html.append(f'<div class="check-line"><span>{k}</span><span class="y">{v}</span></div>')
    if state and state.internet_required and not state.internet_used:
        html.append('<div class="hud-warn">⚠ Internet needed but unavailable — '
                    'add TAVILY_API_KEY to .env. Current-information claims are unverified.</div>')
    html.append("</div>")
    st.markdown("\n".join(html), unsafe_allow_html=True)


# ----------------------------------------------------------------- sources ---
def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.removeprefix("www.") or url[:40]
    except Exception:
        return url[:40]


def _relevance(s: dict) -> str:
    score = s.get("relevance_score")
    if score is None:
        return "—"
    try:
        score = float(score)
    except (TypeError, ValueError):
        return "—"
    return "HIGH" if score >= 0.7 else ("MEDIUM" if score >= 0.4 else "STANDARD")


def render_sources(state) -> None:
    st.markdown('<div class="hud-label">[ SOURCE INTELLIGENCE ]</div>',
                unsafe_allow_html=True)
    sources = (state.sources or []) if state else []
    if not sources:
        st.caption("No citable URLs captured (offline mode or LLM background knowledge).")
        return
    with st.expander(f"▼ SOURCE INTELLIGENCE — {len(sources)} verified records"):
        for i, s in enumerate(sources[:15], 1):
            status = s.get("extraction_status", "")
            icon = {"extracted": "✓", "fallback": "⚠", "failed": "✕"}.get(status, "•")
            word = {"extracted": "EXTRACTION: ✓ COMPLETE",
                    "fallback": "EXTRACTION: ⚠ SNIPPET FALLBACK",
                    "failed": "EXTRACTION: ✕ FAILED"}.get(status, "")
            st.markdown(f"**[{i:02d}] {esc(s.get('title', 'Source'))}**")
            st.caption(f"{_domain(s.get('url', ''))} · RELEVANCE: {_relevance(s)}"
                       + (f" · {word}" if word else ""))
            if s.get("url"):
                st.markdown(f"[{esc(s['url'])}]({esc(s['url'])})")
            if s.get("finding"):
                st.caption(esc(s["finding"])[:300])
            st.markdown("---")


# ------------------------------------------------------------------ console ---
def render_console(state) -> None:
    st.markdown('<div class="hud-label">[ LIVE ACTIVITY ]</div>',
                unsafe_allow_html=True)
    events = (state.events or []) if state else []
    if not events:
        body = '<span class="t">[000]</span> <span class="ok">SYSTEM STANDBY</span> — awaiting objective.'
    else:
        lines = []
        for n, ev in enumerate(events[-14:], 1):
            cls = "warn" if ev.startswith(("RETRY", "Replan")) else "ok"
            lines.append(f'<span class="t">[{n:03d}]</span> '
                         f'<span class="{cls}">{esc(ev)[:220]}</span>')
        body = "<br>".join(lines)
    st.markdown(f'<div class="hud-console">{body}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------- verification --
def render_verification(state) -> None:
    v = ((state.verification or {}) if state else {}) or {}
    passed = bool(v.get("verified"))
    if not v:
        big = '<div class="verify-big fail">○ AWAITING</div>'
    elif passed:
        big = '<div class="verify-big pass">✓ VERIFIED</div>'
    else:
        big = '<div class="verify-big fail">⚠ NEEDS WORK</div>'
    html = ['<div class="hud-panel"><div class="hud-title">◉ VERIFICATION</div>', big]
    if v and not passed and any("research" in (m or "").lower()
                                for m in v.get("missing_items", [])):
        html.append('<div class="hud-dim">REPLANNING — additional research task dispatched.</div>')
    checks = v.get("checks", {}) if v else {}
    for k in ["completeness", "evidence", "consistency", "task_completion"]:
        ok = bool(checks.get(k)) if checks else False
        mark = '<span class="y">✓</span>' if ok else '<span class="n">✕</span>'
        html.append(f'<div class="check-line"><span>{k.upper()}</span><span>{mark}</span></div>')
    html.append(f'<div class="hud-dim">Score: {esc(v.get("score", "n/a")) if v else "n/a"}</div>')
    for issue in (v.get("issues", []) if v else []):
        html.append(f'<div class="hud-dim">- {esc(issue)}</div>')
    html.append("</div>")
    st.markdown("\n".join(html), unsafe_allow_html=True)


# ------------------------------------------------------------------- report ---
def render_report_header(state) -> None:
    lang = getattr(state, "language", "English") if state else "English"
    st.markdown(
        '<div class="hud-panel active"><div class="hud-title">◉ INTELLIGENCE REPORT</div>'
        f'<div class="hud-dim">Report language: {esc(lang)} '
        '(English by default; request another language in your objective)</div></div>',
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------ sidebar ---
def render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="hud-title">◉ AI INTELLIGENCE</div>', unsafe_allow_html=True)
        st.caption("Autonomous Research Command Center")
        st.divider()
        st.markdown('<div class="hud-label">SYSTEM</div>', unsafe_allow_html=True)
        st.write("● ONLINE" if has_api_key() else "○ STANDBY")
        if not has_api_key():
            st.warning("Set OPENROUTER_API_KEY in .env for full LLM power.")
        st.markdown('<div class="hud-label">MODEL</div>', unsafe_allow_html=True)
        # No selector by design — backend auto-resolves a working model.
        st.code(f"OpenRouter / {settings.openrouter_model or '(auto)'}", language="text")
        st.markdown('<div class="hud-label">INTERNET</div>', unsafe_allow_html=True)
        # Config check only — no API call just to render the sidebar.
        st.write("● TAVILY ONLINE" if has_tavily() else "○ TAVILY OFFLINE")
        st.write("● RESEARCH ENABLED" if has_tavily() else "⚠ RESEARCH UNAVAILABLE")
        if not has_tavily():
            st.caption("Add TAVILY_API_KEY to .env to enable web research.")
        st.divider()
        st.markdown('<div class="hud-label">AGENTS — 06 ACTIVE</div>', unsafe_allow_html=True)
        for a in ["Planner", "Researcher", "Analyst", "Executor", "Verifier", "Reporter"]:
            st.write(f"✓ {a}")
        st.divider()
        st.markdown('<div class="hud-label">CONFIGURATION</div>', unsafe_allow_html=True)
        st.slider("Research Rounds", 1, 5, settings.max_research_iterations, disabled=True,
                  help="Configured via .env (MAX_RESEARCH_ITERATIONS)")
        st.slider("Max Retries", 0, 5, settings.max_retries, disabled=True,
                  help="Configured via .env (MAX_RETRIES)")
        st.divider()
        if st.button("↻ NEW INVESTIGATION", use_container_width=True):
            st.session_state["workflow_result"] = None
            st.session_state["running"] = False
            st.rerun()
        st.caption("Local-first · in-memory · v1.0")


def example_labels() -> list:
    return ["Custom Objective"] + [e["title"] for e in EXAMPLES]


def apply_example(choice: str) -> None:
    if choice != "Custom Objective":
        picked = next(e["objective"] for e in EXAMPLES if e["title"] == choice)
        if st.session_state["objective"] != picked:
            st.session_state["objective"] = picked
