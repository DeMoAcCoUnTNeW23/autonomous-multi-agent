"""Analyst agent: turns collected evidence into reasoning.

Compares, finds patterns, connects findings, draws conclusions,
notes limitations. Works from whatever context is available (domain-agnostic).
"""
from __future__ import annotations
from config.settings import get_llm, invoke_llm
from utils.logger import log
from utils.helpers import truncate


def run_analysis(objective: str, research_results: list[str], exec_results: list[str] | None = None,
                 language: str = "English") -> str:
    log("ANALYST", "Analyzing findings...")
    evidence = "\n\n".join([r for r in (research_results or []) if r])[:7000]
    exec_text = "\n\n".join(exec_results or [])[:3000]
    llm = get_llm()
    if llm is None:
        # Heuristic fallback: structure what we have
        parts = [
            "## Analysis (heuristic — no LLM key configured)",
            f"Evidence blocks reviewed: {len(research_results or [])}.",
            "",
            "### Key patterns",
            evidence[:2000] if evidence else "- Insufficient evidence collected.",
            "",
            "### Implications",
            "- Findings should be treated as preliminary until verified with additional sources.",
        ]
        if exec_text:
            parts += ["", "### Execution outputs", truncate(exec_text, 1500)]
        parts += ["", "### Limitations", "- Analysis generated without LLM; configure OPENROUTER_API_KEY for deeper reasoning."]
        log("ANALYST", "Analysis completed (heuristic).")
        return "\n".join(parts)

    try:
        out = invoke_llm(
            llm,
            "You are an Analyst agent. From the evidence, produce: 1) Key patterns (bullets), "
            "2) Comparison of options if relevant, 3) Implications, 4) Conclusions, 5) Limitations. "
            "Be specific, avoid repeating raw evidence verbatim, flag contradictions. "
            f"Write the ENTIRE output in {language}. No other language.",
            f"Objective: {objective}\n\nResearch evidence:\n{evidence}\n\nExecution outputs:\n{exec_text}",
        )
        log("ANALYST", "Analysis completed.")
        return out
    except Exception as e:
        log("ANALYST", f"LLM analysis failed: {e}")
        return f"Analysis failed ({e}). Raw evidence:\n{truncate(evidence, 3000)}"
