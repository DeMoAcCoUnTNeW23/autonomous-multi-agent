"""Researcher agent: deep, iterative Internet research loop.

Research Objective -> Generate Query -> Tavily Search -> Review Results ->
Select Relevant Sources -> Extract Web Content (BeautifulSoup, with Tavily
snippet fallback) -> Analyze Evidence -> Gaps? Follow-up search : Finish.

Queries are generated dynamically from the task (LLM or heuristic), never
hard-coded. Bounded by MAX_RESEARCH_ITERATIONS; MAX_SOURCES caps fetching
so the LLM only sees ranked, cleaned evidence.
"""
from __future__ import annotations
from urllib.parse import urlparse
from config.settings import get_llm, invoke_llm, settings, has_tavily
from tools.tool_registry import execute_tool
from tools.web.models import WebSource
from utils.logger import log
from utils.helpers import truncate


def _followups_llm(llm, question: str, so_far: str) -> list[str]:
    try:
        raw = invoke_llm(
            llm,
            "You are a research strategist. Given the question and findings so far, "
            "propose up to 2 specific follow-up web-search queries that fill gaps. "
            "Return them as plain lines, no numbering.",
            f"Question: {question}\nFindings so far:\n{truncate(so_far, 2000)}",
            max_tokens=300,
        )
        qs = [l.strip("-•1234567890. ").strip() for l in raw.splitlines() if len(l.strip()) > 10]
        return qs[:2]
    except Exception:
        return []


def _heuristic_followups(question: str, iteration: int) -> list[str]:
    """Fallback query variants when no LLM is available (still dynamic)."""
    q = question[:120]
    variants = [f"{q} recent developments", f"{q} comparison review"]
    return [variants[iteration - 1]] if iteration <= len(variants) else []


def _normalize(raw: list[dict]) -> list[WebSource]:
    """Convert Tavily or legacy search results into WebSource objects."""
    out = []
    for r in raw or []:
        url = (r.get("url") or "").strip()
        if not url:
            continue  # offline-fallback entries carry no URL
        score = r.get("score")
        try:
            score = float(score) if score is not None else None
        except (TypeError, ValueError):
            score = None
        out.append(WebSource(
            title=r.get("title", "") or url,
            url=url,
            snippet=r.get("content", "") or r.get("snippet", ""),
            source_type="web",
            relevance_score=score,
        ))
    return out


def _select(candidates: list[WebSource], seen: set[str]) -> list[WebSource]:
    """Rank by relevance score, drop duplicates/domains repeats, cap at MAX_SOURCES."""
    fresh = [c for c in candidates if c.url not in seen]
    fresh.sort(key=lambda s: (s.relevance_score is not None, s.relevance_score or 0),
               reverse=True)
    picked, domains = [], set()
    for c in fresh:
        try:
            dom = urlparse(c.url).netloc.lower().removeprefix("www.")
        except Exception:
            dom = ""
        if dom and dom in domains:
            continue  # prefer domain diversity
        picked.append(c)
        if dom:
            domains.add(dom)
        if len(picked) >= settings.max_sources:
            break
    return picked


def _extract(source: WebSource) -> WebSource:
    """Fetch + extract page content; fall back to Tavily snippet on failure."""
    res = execute_tool("researcher", "web_fetch", url=source.url)
    if isinstance(res, dict) and res.get("status") == "extracted" and res.get("text"):
        source.extracted_text = truncate(res["text"], settings.max_content_chars)
        source.source_type = "web"
        source.extraction_status = "extracted"
    else:
        # Robust fallback: Tavily-provided content keeps the workflow going.
        err = res.get("error", "unknown") if isinstance(res, dict) else str(res)
        source.source_type = "tavily-fallback" if source.snippet else "web"
        source.extraction_status = "fallback" if source.snippet else "failed"
        source.error = truncate(str(err), 200)
        log("RESEARCHER", f"Extraction failed for {source.url[:60]} — using Tavily snippet. ({err})"[:160])
    return source


def run_research(task_description: str, context: str = "", max_iterations: int | None = None,
                 use_internet: bool | None = None, language: str = "English") -> dict:
    """Run iterative research. Returns {findings, sources, iterations, unanswered,
    web_stats, internet_used, offline}."""
    max_iterations = max_iterations or settings.max_research_iterations
    log("RESEARCHER", f"Starting research task: {task_description[:80]}...")
    llm = get_llm()
    internet = has_tavily() if use_internet is None else (bool(use_internet) and has_tavily())
    if use_internet and not has_tavily():
        log("RESEARCHER", "Internet requested but Tavily not configured — legacy/offline search.")

    queries = [task_description]
    if context:
        queries[0] = f"{task_description}. Context: {truncate(context, 300)}"

    all_sources: list[WebSource] = []
    seen_urls: set[str] = set()
    stats = {"iterations": 0, "found": 0, "selected": 0, "extracted": 0, "fallbacks": 0}

    for it in range(1, max_iterations + 1):
        query = queries[0] if it == 1 else (queries[-1] if len(queries) >= it else task_description)
        results = execute_tool("researcher", "web_search", query=query,
                               max_results=settings.max_web_results)
        if isinstance(results, str):  # permission denied / error string
            log("RESEARCHER", f"Search problem: {results[:120]}")
            break
        candidates = _normalize(results if isinstance(results, list) else [])
        stats["found"] += len(candidates)
        picked = _select(candidates, seen_urls)
        stats["selected"] += len(picked)
        log("RESEARCHER",
            f"Iteration {it}/{max_iterations}: query='{query[:60]}' "
            f"{len(candidates)} found -> {len(picked)} selected.")
        for src in picked:
            seen_urls.add(src.url)
            all_sources.append(_extract(src))
            if src.extraction_status == "extracted":
                stats["extracted"] += 1
            else:
                stats["fallbacks"] += 1
        stats["iterations"] = it
        if not picked:
            break  # nothing new — stop early
        # Gaps? generate follow-up queries dynamically.
        if it < max_iterations:
            if llm is not None:
                fups = _followups_llm(
                    llm, task_description,
                    "\n".join(s.evidence_text()[:400] for s in all_sources))
                if not fups:
                    break
                queries.extend(fups)
            else:
                queries.extend(_heuristic_followups(task_description, it))

    # Build research context: structured evidence, not a raw dump.
    blocks = []
    for i, s in enumerate(all_sources, 1):
        blocks.append(
            f"SOURCE [{i}]\nTitle: {s.title}\nURL: {s.url}\n"
            f"Content:\n{truncate(s.evidence_text(), 2500)}")
    evidence_ctx = "\n\n".join(blocks)

    if llm is not None and evidence_ctx:
        try:
            findings_text = invoke_llm(
                llm,
                "You are a Researcher. Answer the research question using ONLY the provided "
                "sources. Produce: 1) Findings as bullets, each tied to source numbers like [1], [3]; "
                "2) a Confidence note per finding (high/medium/low); 3) Contradictions between "
                "sources if any. Never invent citations — use only the numbered sources given. "
                f"Write the ENTIRE output in {language}. No other language.",
                f"Question: {task_description}\n\nEvidence:\n{truncate(evidence_ctx, 9000)}",
            )
        except Exception as e:
            findings_text = evidence_ctx[:4000] + f"\n(Synthesis LLM failed: {e})"
    elif evidence_ctx:
        findings_text = "## Evidence (heuristic — no LLM key configured)\n\n" + evidence_ctx[:4000]
    else:
        findings_text = ("No web evidence could be retrieved. Tavily is not configured or the "
                         "network is unavailable — findings would be unreliable, so none are fabricated.")

    offline = not all_sources
    log("RESEARCHER",
        f"Research done: {stats['iterations']} iterations, {stats['found']} found, "
        f"{stats['selected']} selected, {stats['extracted']} extracted.")
    return {
        "findings": findings_text,
        "sources": [s.to_state_dict() for s in all_sources if s.url],
        "iterations": stats["iterations"],
        "unanswered": [] if len(all_sources) >= 2 else [
            "Evidence is thin — treat conclusions as preliminary."],
        "web_stats": stats,
        "internet_used": internet and not offline,
        "offline": offline,
    }
