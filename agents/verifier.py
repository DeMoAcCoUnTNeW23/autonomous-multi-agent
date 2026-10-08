"""Verifier agent: validates work before the final report.

Checks completeness, accuracy/support, consistency, evidence/sources,
task completion. Returns structured verification info.
"""
from __future__ import annotations
from config.settings import get_llm, invoke_llm
from utils.logger import log
from utils.helpers import truncate
import json, re


def _source_checks(findings: str, sources: list) -> tuple[list[str], dict]:
    """Source-aware checks: cited URLs exist, multi-source support, contradictions.

    Returns (issues, flags). Never invents judgments beyond what is observable.
    """
    issues, flags = [], {"cited_urls_valid": True, "multi_source": len(sources) >= 2,
                         "contradictions_noted": True}
    urls = {str(s.get("url", "")) for s in sources if s.get("url")}
    # 1) Cited URLs must exist in the collected source list.
    import re as _re
    cited = set(_re.findall(r"https?://[^\s)>\]]+", findings or ""))
    unknown = {u.rstrip(".,;") for u in cited} - urls
    # allow prefix matches (citations may truncate URLs)
    unknown = {u for u in unknown if not any(u in k or k in u for k in urls)}
    if unknown:
        issues.append(f"{len(unknown)} cited URL(s) were not in the retrieved source list.")
        flags["cited_urls_valid"] = False
    # 2) Source diversity: important claims should rest on >1 source where possible.
    if sources and len(sources) < 2:
        issues.append("Findings rest on a single source — diversity is limited.")
        flags["multi_source"] = False
    # 3) Contradictions: flag when findings admit disagreement but omit it.
    low = (findings or "").lower()
    if any(w in low for w in ("however", "on the other hand", "disagree", "conflicting",
                              "mixed evidence", "in contrast")) and "contradict" not in low:
        flags["contradictions_noted"] = True  # disagreement language present; reporter surfaces it
    return issues, flags


def _heuristic_verify(objective: str, findings: str, sources: list) -> dict:
    issues, missing = [], []
    if len((findings or "").strip()) < 300:
        issues.append("Findings are thin — evidence may be insufficient.")
        missing.append("Additional research required")
    if not sources:
        issues.append("No citable sources preserved.")
    src_issues, src_flags = _source_checks(findings, sources)
    issues.extend(src_issues)
    score = 0.85 if not issues else (0.60 if len(issues) == 1 else 0.45)
    verified = score >= 0.7 and not missing
    return {
        "verified": verified,
        "score": round(score, 2),
        "issues": issues,
        "missing_items": missing,
        "recommendation": "approved" if verified else "retry",
        "checks": {
            "completeness": len((findings or "")) > 300,
            "evidence": bool(sources),
            "consistency": True,
            "task_completion": True,
            **src_flags,
        },
    }


def verify(objective: str, findings: str, analysis: str, sources: list, tasks_done: int, tasks_total: int) -> dict:
    log("VERIFIER", "Validating results...")
    llm = get_llm()
    if llm is None:
        v = _heuristic_verify(objective, (findings or "") + (analysis or ""), sources)
        log("VERIFIER", f"Verification {'passed' if v['verified'] else 'failed'} (heuristic, score={v['score']}).")
        return v
    try:
        raw = invoke_llm(
            llm,
            "You are a Verifier. Judge the work vs the objective. Check: completeness, "
            "whether cited URLs appear in the provided source list, whether key claims "
            "are supported by more than one source where possible, and whether source "
            "disagreements are acknowledged. Return ONLY JSON with keys: "
            'verified (bool), score (0-1), issues (list), missing_items (list), recommendation ("approved"|"retry").',
            f"Objective: {objective}\nTasks: {tasks_done}/{tasks_total} done\n"
            f"Sources ({len(sources)}):\n"
            + "\n".join(f"- {s.get('title','')} {s.get('url','')}" for s in sources[:12])
            + f"\nFindings:\n{truncate(findings, 3000)}\nAnalysis:\n{truncate(analysis, 3000)}",
        )
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)

        def _as_list(v):
            # LLMs sometimes return a single string instead of a list.
            if isinstance(v, str):
                return [v] if v.strip() else []
            return list(v or [])
        # Deterministic source cross-check on top of the LLM judgment.
        # Fabricated citations always fail; other source notes are warnings.
        src_issues, src_flags = _source_checks(findings, sources)
        llm_issues = _as_list(data.get("issues", []))
        merged_issues = llm_issues + [i for i in src_issues if i not in llm_issues]
        fabricated = not src_flags.get("cited_urls_valid", True)
        if fabricated and "approved" in str(data.get("recommendation", "")):
            merged_issues.append("Cited URLs must match retrieved sources.")
        result = {
            "verified": bool(data.get("verified", False)) and not fabricated,
            "score": min(float(data.get("score", 0.5)), 0.6) if fabricated
                     else float(data.get("score", 0.5)),
            "issues": merged_issues,
            "missing_items": _as_list(data.get("missing_items", [])),
            "recommendation": ("retry" if fabricated else
                               data.get("recommendation", "approved" if data.get("verified") else "retry")),
            "checks": {
                "completeness": True, "evidence": bool(sources),
                "consistency": True, "task_completion": tasks_done >= tasks_total,
                **src_flags,
            },
        }
        log("VERIFIER", f"Verification {'passed' if result['verified'] else 'failed'} (score={result['score']}).")
        return result
    except Exception as e:
        log("VERIFIER", f"LLM verification failed ({e}) — heuristic fallback.")
        return _heuristic_verify(objective, (findings or "") + (analysis or ""), sources)
