from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SourceAnalysisStatus(StrEnum):
    RESOLVED = "resolved"
    INFERRED_FROM_LOG = "inferred_from_log"
    MULTIPLE_CANDIDATES = "multiple_candidates"
    NOT_FOUND = "not_found"
    NOT_CONFIGURED = "not_configured"
    LOOKUP_FAILED = "lookup_failed"


class LogSourceHint(BaseModel):
    path: str | None = None
    filename: str | None = None
    function: str | None = None
    line_number: int | None = None
    excerpt: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class SourceCandidate(BaseModel):
    repository: str
    owner: str | None = None
    path: str
    ref: str | None = None
    content_sha: str | None = None
    function: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    snippet: str | None = None
    source_url: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    match_reason: str


class SourceAnalysis(BaseModel):
    status: SourceAnalysisStatus
    provider: str = "log"
    github_enabled: bool = False
    repository: str | None = None
    owner: str | None = None
    path: str | None = None
    ref: str | None = None
    content_sha: str | None = None
    function: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    snippet: str | None = None
    source_url: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    match_reason: str | None = None
    explanation: str | None = None
    lookup_message: str | None = None
    inferred_hints: list[LogSourceHint] = Field(default_factory=list, max_length=8)
    candidates: list[SourceCandidate] = Field(default_factory=list, max_length=5)
