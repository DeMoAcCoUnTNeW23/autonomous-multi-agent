"""Pydantic schemas for the final report (internal structure, not user output)."""
from __future__ import annotations
from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    title: str = ""
    url: str = ""
    finding: str = ""


class VerificationInfo(BaseModel):
    verified: bool = False
    score: float = 0.0
    issues: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    recommendation: str = "retry"


class ReportData(BaseModel):
    title: str
    objective: str
    executive_summary: str = ""
    key_findings: list[str] = Field(default_factory=list)
    analysis: str = ""
    recommendations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    conclusion: str = ""
    sources: list[SourceItem] = Field(default_factory=list)
    verification: VerificationInfo = Field(default_factory=VerificationInfo)
