"""Reporter agent: converts verified workflow state into a professional report.

Chooses sections appropriate to the objective. Never dumps raw agent
chatter or internal JSON — produces clean Markdown for humans.
"""
from __future__ import annotations
from config.settings import get_llm, invoke_llm
from utils.logger import log
from utils.helpers import truncate


DEFAULT_SECTIONS = [
    "Executive Summary", "Objective", "Research Approach", "Key Findings",
    "Detailed Analysis", "Recommendations", "Limitations", "Conclusion",
    "Sources", "Verification Status",
]


def _fallback_report(objective, findings, analysis, exec_out, sources, verification,
                     method_note: str = "") -> str:
    src_lines = "\n".join(
        f"{i+1}. [{s.get('title','Source')}]({s.get('url','')})" for i, s in enumerate(sources[:15])
    ) or "No external sources captured (offline or no research tool results)."
    v = verification or {}
    method = method_note or (
        "The planner decomposed the objective into subtasks executed by researcher, analyst, "
        "and executor agents with controlled tool use. Findings were verified before reporting.")
    return f"""# Research Report: {objective[:90]}

## Executive Summary

This report addresses the objective stated below, based on autonomous research and analysis performed by the multi-agent workflow.

## 1. Objective

{objective}

## 2. Research Method

{method}

## 3. Key Findings

{truncate(findings, 4000)}

## 4. Detailed Analysis

{truncate(analysis, 4000)}

## 5. Execution Results

{truncate(exec_out, 2000) if exec_out else "No computation/file execution was required for this objective."}

## 6. Recommendations

- Treat findings above as the evidence base; validate critical decisions with primary sources.
- Configure `OPENROUTER_API_KEY` for deeper LLM-powered synthesis.

## 7. Limitations

- {(chr(10)+"- ").join((v.get("issues") or ["Evidence may be incomplete; sources limited."]))}
- Time-bounded automated research; not a substitute for domain-expert review.

## 8. Conclusion

The collected evidence and analysis provide a working answer to the objective. Further targeted research can deepen any section on request.

## 9. Sources

{src_lines}

## 10. Verification

Status: {"PASSED" if v.get("verified") else "NEEDS REVIEW"} (score {v.get("score", "n/a")})
Issues: {", ".join(v.get("issues") or ["None"])}
"""


def generate_report(objective, findings, analysis, exec_out, sources, verification,
                    method_note: str = "", language: str = "English") -> str:
    """Produce the final Markdown report.

    The LLM always structures the report first (primary path). The static
    template below is a last-resort fallback used only when the LLM fails.
    """
    log("REPORTER", f"Generating final report in {language} (LLM-structured)...")
    llm = get_llm()
    if llm is None:
        log("REPORTER", "No LLM — report generated (template fallback).")
        return _fallback_report(objective, findings, analysis, exec_out, sources,
                                verification, method_note)
    try:
        v = verification or {}
        src = "\n".join(f"- {s.get('title')}: {s.get('url')}" for s in (sources or [])[:15])
        report = invoke_llm(
            llm,
            "You are a Reporter agent. You structure the final report — organize the "
            "given findings and analysis into a professional Markdown document with a "
            "clear section hierarchy. Adapt sections to the objective (skip irrelevant "
            "ones like Comparison when not needed) but always include: "
            "title (#), Executive Summary, Objective, Research Method (how the web was searched, "
            "how many sources were selected/extracted), Key Findings (each tied to its source), "
            "Detailed Analysis, Recommendations, "
            "Limitations, Conclusion, Sources (use ONLY the provided URLs, never invent), Verification Status. "
            "If sources disagree, say so explicitly. "
            "Clean hierarchy with ## / ### headings, tables where comparison helps, "
            "no internal JSON, no chain-of-thought, no raw agent chatter. "
            f"Write the ENTIRE report in {language}. No other language anywhere in the report.",
            f"Objective: {objective}\n\nResearch method: {method_note}\n\n"
            f"Findings:\n{truncate(findings, 5000)}\n\n"
            f"Analysis:\n{truncate(analysis, 4000)}\n\nExecution:\n{truncate(exec_out, 2000)}\n\n"
            f"Sources:\n{src}\n\nVerification: {v}",
            max_tokens=4000,
        )
        # Safety: ensure sources section exists
        if "## " not in report:
            raise ValueError("malformed report")
        log("REPORTER", "Report generated.")
        return report
    except Exception as e:
        log("REPORTER", f"LLM report failed ({e}) — template fallback.")
        return _fallback_report(objective, findings, analysis, exec_out, sources,
                                verification, method_note)
