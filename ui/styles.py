"""Centralized CSS for the futuristic AI Intelligence interface.

All visual styling lives here — app.py only calls inject_styles() once.
Palette: black / deep green / neon green. Red/orange reserved for warnings.
"""
import streamlit as st

FONTS_LINK = (
    '<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;800&family=Share+Tech+Mono&display=swap"'
    ' rel="stylesheet">'
)

CSS = """
:root {
    --bg0: #020706;
    --bg1: #03100C;
    --bg2: #06140F;
    --neon: #00FF66;
    --neon2: #00C853;
    --soft: #39FF88;
    --dim: #0B6B3A;
    --ink: #E8FFF1;
    --muted: #7DAF91;
    --border: rgba(0, 255, 102, 0.20);
    --glow: rgba(0, 255, 102, 0.30);
}

/* ---------- app background: grid + glow + vignette ---------- */
.stApp {
    background:
        radial-gradient(1100px 500px at 50% -8%, rgba(0,255,102,0.10), transparent 60%),
        radial-gradient(800px 600px at 85% 110%, rgba(0,200,83,0.07), transparent 60%),
        linear-gradient(rgba(0,255,102,0.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,102,0.045) 1px, transparent 1px),
        linear-gradient(var(--bg0), var(--bg1));
    background-size: auto, auto, 44px 44px, 44px 44px, auto;
    color: var(--ink);
    font-family: "Share Tech Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

/* ---------- scanlines overlay (subtle, non-interactive) ---------- */
.stApp::after {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 999;
    background: repeating-linear-gradient(
        to bottom,
        rgba(255,255,255,0.022) 0px,
        rgba(255,255,255,0.022) 1px,
        transparent 1px,
        transparent 4px
    );
}

/* ---------- hide default chrome (functionality untouched) ---------- */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stHeader"] { display: none; }

/* ---------- sidebar = control panel ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(rgba(3,16,12,0.96), rgba(2,7,6,0.98));
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] label { color: var(--ink) !important; }

/* ---------- headings ---------- */
h1, h2, h3, .hud-hero, .hud-brand {
    font-family: "Orbitron", "Share Tech Mono", ui-monospace, monospace !important;
    letter-spacing: 0.08em;
    color: var(--ink) !important;
}

/* ---------- panels ---------- */
.hud-panel {
    background: rgba(3, 16, 12, 0.72);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px 20px;
    margin: 12px 0;
    box-shadow: 0 0 10px rgba(0,255,102,0.08), inset 0 0 24px rgba(0,255,102,0.03);
    backdrop-filter: blur(2px);
}
.hud-panel.active {
    border-color: rgba(0,255,102,0.60);
    box-shadow: 0 0 14px rgba(0,255,102,0.25), 0 0 40px rgba(0,255,102,0.08);
}
.hud-label {
    font-size: 11px;
    letter-spacing: 0.28em;
    color: var(--muted);
    margin-bottom: 6px;
}
.hud-title {
    font-family: "Orbitron", monospace;
    font-size: 15px;
    letter-spacing: 0.18em;
    color: var(--soft);
    margin-bottom: 10px;
}
.hud-dim { color: var(--muted); font-size: 13px; }
.hud-warn {
    color: #FFB300;
    font-size: 13px;
    border: 1px solid rgba(255, 179, 0, 0.4);
    border-radius: 6px;
    padding: 8px 10px;
    margin-top: 10px;
    background: rgba(255, 179, 0, 0.06);
}
.glow-text { color: var(--neon); text-shadow: 0 0 12px var(--glow); }

/* ---------- hero ---------- */
.hud-hero {
    text-align: center;
    padding: 34px 10px 22px 10px;
}
.hud-hero h1 {
    font-size: clamp(38px, 6vw, 74px) !important;
    font-weight: 800;
    margin: 0;
    line-height: 1.05;
    color: var(--ink) !important;
    text-shadow: 0 0 22px rgba(0,255,102,0.35);
}
.hud-hero h1 .neon { color: var(--neon); }
.hud-hero .tagline {
    letter-spacing: 0.5em;
    color: var(--soft);
    font-size: 13px;
    margin-top: 10px;
}
.hud-hero .sub { color: var(--muted); margin-top: 12px; font-size: 14px; }
.hud-rule {
    height: 1px;
    margin: 18px auto;
    max-width: 560px;
    background: linear-gradient(90deg, transparent, var(--neon), transparent);
    box-shadow: 0 0 12px var(--glow);
}
.hud-telemetry {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 22px;
    justify-content: center;
    color: var(--muted);
    font-size: 12px;
    letter-spacing: 0.14em;
}
.hud-telemetry b { color: var(--soft); font-weight: normal; }

/* ---------- top header bar ---------- */
.hud-topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 18px;
    background: rgba(3,16,12,0.8);
    font-size: 13px;
    letter-spacing: 0.2em;
    margin-bottom: 6px;
}
.hud-topbar .brand { font-family: "Orbitron", monospace; color: var(--ink); font-weight: 700; }
.hud-topbar .ok { color: var(--neon); text-shadow: 0 0 10px var(--glow); }

/* ---------- telemetry strip ---------- */
.tele-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 10px;
    margin: 12px 0;
}
.tele-cell {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 6px;
    text-align: center;
    background: rgba(3,16,12,0.7);
}
.tele-cell .k { font-size: 10px; letter-spacing: 0.24em; color: var(--muted); }
.tele-cell .v {
    font-family: "Orbitron", monospace;
    font-size: 20px;
    color: var(--neon);
    text-shadow: 0 0 10px var(--glow);
    margin-top: 4px;
}

/* ---------- workflow timeline ---------- */
.flow { display: flex; flex-direction: column; align-items: stretch; gap: 0; }
.flow-node {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    background: rgba(3,16,12,0.75);
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.flow-node .name { font-family: "Orbitron", monospace; letter-spacing: 0.2em; font-size: 13px; }
.flow-node .stt { font-size: 13px; letter-spacing: 0.12em; }
.flow-node.done { border-color: rgba(0,255,102,0.45); }
.flow-node.done .stt { color: var(--neon); }
.flow-node.run {
    border-color: var(--neon);
    box-shadow: 0 0 14px rgba(0,255,102,0.35), 0 0 44px rgba(0,255,102,0.10);
    animation: hud-pulse 1.6s ease-in-out infinite;
}
.flow-node.run .stt { color: var(--neon); text-shadow: 0 0 10px var(--glow); }
.flow-node.idle .stt { color: var(--muted); }
.flow-node.warn .stt { color: #FFB300; }
.flow-node.fail { border-color: rgba(255,70,70,0.6); }
.flow-node.fail .stt { color: #FF6B6B; }
.flow-link { text-align: center; color: var(--dim); line-height: 1; font-size: 14px; }
@keyframes hud-pulse {
    0%, 100% { box-shadow: 0 0 8px rgba(0,255,102,0.20); }
    50% { box-shadow: 0 0 20px rgba(0,255,102,0.45), 0 0 60px rgba(0,255,102,0.12); }
}

/* ---------- agent cards ---------- */
.agent-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
.agent-card {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
    background: rgba(3,16,12,0.7);
}
.agent-card .an { font-family: "Orbitron", monospace; font-size: 13px; letter-spacing: 0.18em; color: var(--soft); }
.agent-card .row { display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); margin-top: 6px; }
.agent-card .row b { color: var(--ink); font-weight: normal; }
.agent-card .note { font-size: 12px; color: var(--muted); margin-top: 8px; min-height: 18px; }
.agent-card.lit { border-color: rgba(0,255,102,0.55); box-shadow: 0 0 12px rgba(0,255,102,0.22); }

/* ---------- console ---------- */
.hud-console {
    background: rgba(0,0,0,0.55);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 12.5px;
    line-height: 1.7;
    max-height: 260px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
}
.hud-console .t { color: var(--dim); }
.hud-console .ok { color: var(--soft); }
.hud-console .warn { color: #FFB300; }

/* ---------- verification ---------- */
.verify-big {
    text-align: center;
    font-family: "Orbitron", monospace;
    font-size: 26px;
    letter-spacing: 0.2em;
    padding: 10px 0 4px 0;
}
.verify-big.pass { color: var(--neon); text-shadow: 0 0 18px var(--glow); }
.verify-big.fail { color: #FFB300; }
.check-line {
    display: flex;
    justify-content: space-between;
    border-bottom: 1px dashed rgba(0,255,102,0.14);
    padding: 7px 2px;
    font-size: 13px;
    letter-spacing: 0.1em;
}
.check-line .y { color: var(--neon); }
.check-line .n { color: #FF6B6B; }

/* ---------- report (rendered inside st.container(border=True)) ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(0,255,102,0.35) !important;
    border-radius: 12px;
    background: rgba(2, 10, 7, 0.85);
    box-shadow: 0 0 18px rgba(0,255,102,0.12);
    padding: 12px 26px 20px 26px;
}
[data-testid="stVerticalBlockBorderWrapper"] h1 { font-size: 26px !important; color: var(--ink) !important; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
[data-testid="stVerticalBlockBorderWrapper"] h2 { font-size: 18px !important; color: var(--soft) !important; margin-top: 22px; }
[data-testid="stVerticalBlockBorderWrapper"] h3 { font-size: 15px !important; color: var(--soft) !important; }
[data-testid="stVerticalBlockBorderWrapper"] p,
[data-testid="stVerticalBlockBorderWrapper"] li { color: #D6F5E2 !important; font-size: 14.5px; line-height: 1.65; }
[data-testid="stVerticalBlockBorderWrapper"] table { width: 100%; border-collapse: collapse; font-size: 13px; }
[data-testid="stVerticalBlockBorderWrapper"] th,
[data-testid="stVerticalBlockBorderWrapper"] td { border: 1px solid var(--border); padding: 7px 10px; }
[data-testid="stVerticalBlockBorderWrapper"] th { color: var(--neon); background: rgba(0,255,102,0.06); }
[data-testid="stVerticalBlockBorderWrapper"] a { color: var(--neon) !important; }
[data-testid="stVerticalBlockBorderWrapper"] code { color: var(--soft) !important; background: rgba(0,255,102,0.08) !important; }

/* ---------- inputs & buttons ---------- */
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input {
    background: rgba(0,0,0,0.55) !important;
    color: var(--soft) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    caret-color: var(--neon);
}
[data-testid="stTextArea"] textarea:focus, [data-testid="stTextInput"] input:focus {
    border-color: var(--neon) !important;
    box-shadow: 0 0 0 1px var(--neon), 0 0 22px rgba(0,255,102,0.25) !important;
}
div.stButton > button {
    background: rgba(0,255,102,0.06) !important;
    color: var(--soft) !important;
    border: 1px solid rgba(0,255,102,0.45) !important;
    border-radius: 8px !important;
    letter-spacing: 0.18em;
    font-family: "Orbitron", monospace !important;
    transition: box-shadow 0.2s, background 0.2s;
}
div.stButton > button:hover {
    background: rgba(0,255,102,0.14) !important;
    box-shadow: 0 0 16px rgba(0,255,102,0.35) !important;
    color: #FFFFFF !important;
}
div.stButton > button[kind="primary"] {
    background: rgba(0,255,102,0.16) !important;
    border-color: var(--neon) !important;
    color: #FFFFFF !important;
    box-shadow: 0 0 14px rgba(0,255,102,0.30) !important;
}
div.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 26px rgba(0,255,102,0.55) !important;
}

/* ---------- streamlit natives tuned to theme ---------- */
[data-testid="stMetric"] { background: rgba(3,16,12,0.6); border: 1px solid var(--border); border-radius: 8px; padding: 8px; }
[data-testid="stMetricLabel"] { color: var(--muted) !important; }
[data-testid="stMetricValue"] { color: var(--soft) !important; font-family: "Orbitron", monospace !important; }
[data-testid="stExpander"] { border: 1px solid var(--border) !important; border-radius: 8px; background: rgba(3,16,12,0.6); }
[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 8px; }
.stAlert { background: rgba(3,16,12,0.85) !important; border: 1px solid var(--border) !important; color: var(--ink) !important; }
a { color: var(--neon) !important; }
[data-testid="stProgressBar"] > div > div { background: var(--neon) !important; box-shadow: 0 0 10px var(--glow); }
[data-testid="stSelectbox"] div[data-baseweb="select"] { background: rgba(0,0,0,0.5) !important; border: 1px solid var(--border); border-radius: 8px; }
hr { border-color: rgba(0,255,102,0.15) !important; }

@media (max-width: 768px) {
    .hud-hero h1 { letter-spacing: 0.04em; }
    [data-testid="stVerticalBlockBorderWrapper"] { padding: 8px 14px 14px 14px; }
}
"""


def inject_styles() -> None:
    """Load fonts + theme CSS. Call once at the top of app.py."""
    st.markdown(FONTS_LINK, unsafe_allow_html=True)
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
