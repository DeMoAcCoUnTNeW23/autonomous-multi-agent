"""Structured web-evidence model shared by the Internet research pipeline."""
from __future__ import annotations
from pydantic import BaseModel, Field


class WebSource(BaseModel):
    """One unit of web evidence, from discovery through extraction."""
    title: str = ""
    url: str = ""
    snippet: str = ""            # Tavily/DuckDuckGo-provided summary
    extracted_text: str = ""     # BeautifulSoup page content (may be empty)
    source_type: str = "web"     # web | tavily-fallback | offline-fallback
    relevance_score: float | None = None
    extraction_status: str = "pending"  # pending | extracted | fallback | failed
    error: str = ""

    def evidence_text(self) -> str:
        """Best available content for the LLM: full text, else snippet."""
        return self.extracted_text or self.snippet

    def to_state_dict(self) -> dict:
        """Compact dict stored in WorkflowState.sources (backward compatible)."""
        return {
            "title": self.title,
            "url": self.url,
            "finding": (self.extracted_text[:300] if self.extracted_text
                        else self.snippet[:300]),
            "snippet": self.snippet[:500],
            "source_type": self.source_type,
            "relevance_score": self.relevance_score,
            "extraction_status": self.extraction_status,
        }
