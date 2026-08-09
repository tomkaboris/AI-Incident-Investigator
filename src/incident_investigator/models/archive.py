from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from incident_investigator.models.incident import (
    IncidentCategory,
    IncidentSeverity,
)
from incident_investigator.source_analysis.models import SourceAnalysis


class ArtifactEvidence(BaseModel):
    artifact_id: int | None = None
    path: str
    line_start: int | None = None
    line_end: int | None = None
    timestamp_utc: datetime | None = None
    excerpt: str
    explanation: str


class CorrelatedEvent(BaseModel):
    timestamp_utc: datetime | None = None
    component: str
    event: str
    relationship: str
    artifact_paths: list[str] = Field(default_factory=list)


class ArchiveIncidentAnalysis(BaseModel):
    title: str
    executive_summary: str
    category: IncidentCategory
    severity: IncidentSeverity
    probable_root_cause: str
    root_cause_component: str | None = None
    affected_components: list[str] = Field(default_factory=list)
    causal_chain: list[str] = Field(default_factory=list, max_length=12)
    correlated_events: list[CorrelatedEvent] = Field(default_factory=list, max_length=30)
    supporting_evidence: list[ArtifactEvidence] = Field(default_factory=list, max_length=20)
    conflicting_evidence: list[ArtifactEvidence] = Field(default_factory=list, max_length=10)
    missing_information: list[str] = Field(default_factory=list, max_length=10)
    immediate_actions: list[str] = Field(default_factory=list, max_length=8)
    long_term_actions: list[str] = Field(default_factory=list, max_length=8)
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool = True
    analyzed_time_window_start: datetime | None = None
    analyzed_time_window_end: datetime | None = None
    markdown_report: str
    source_analysis: SkipJsonSchema[SourceAnalysis | None] = None


class ArchiveCreatedResponse(BaseModel):
    incident_id: str
    archive_id: int
    status: str
    uploaded_filename: str
    problem_description: str
    incident_time: datetime | None
    timezone: str
    system_name: str | None
    artifact_count: int
    total_extracted_size_bytes: int
    max_depth_reached: int
    analysis: ArchiveIncidentAnalysis
    provider_name: str
    model_name: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    cost_status: str = "usage_unavailable"
    cost_currency: str = "USD"
    pricing_source: str | None = None


class ArtifactResponse(BaseModel):
    id: int
    original_path: str
    source_archive_path: str | None
    archive_depth: int
    filename: str
    extension: str | None
    content_type: str | None
    size_bytes: int
    checksum_sha256: str
    component: str | None
    log_format: str | None
    encoding: str | None
    earliest_timestamp: datetime | None
    latest_timestamp: datetime | None
    is_archive: bool
    is_log_candidate: bool
    processing_status: str


class TimelineEventResponse(BaseModel):
    artifact_id: int
    path: str
    component: str
    timestamp_utc: datetime | None
    original_timestamp: str | None
    severity: str | None
    message: str
    line_number: int | None
    correlation_ids: list[str] = Field(default_factory=list)


class ArchiveAnalysisStoredResponse(BaseModel):
    incident_id: str
    archive_id: int
    uploaded_filename: str
    incident_time: datetime | None
    timezone: str
    system_name: str | None
    artifact_count: int
    total_extracted_size_bytes: int
    max_depth_reached: int
    provider_name: str
    model_name: str
    analysis: dict[str, Any]
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    cost_status: str = "usage_unavailable"
    cost_currency: str = "USD"
    pricing_source: str | None = None
    created_at: datetime
