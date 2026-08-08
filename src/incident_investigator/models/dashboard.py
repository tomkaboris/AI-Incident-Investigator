from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IncidentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: str
    filename: str
    problem_description: str | None
    category: str
    severity: str
    summary: str
    probable_root_cause: str
    confidence: float
    log_storage_backend: str
    log_size_bytes: int
    created_at: datetime
    created_by_name: str
    assigned_to_name: str | None = None
    investigation_count: int = 0
    latest_root_cause_confidence: float | None = None
    requires_human_review: bool = False


class DashboardOverview(BaseModel):
    total_incidents: int
    open_incidents: int
    critical_incidents: int
    investigations_total: int
    human_review_required: int
    average_confidence: float
    average_analysis_duration_ms: float | None
    storage_bytes: int
    incidents_by_severity: dict[str, int]
    incidents_by_category: dict[str, int]
    recent_incidents: list[IncidentListItem]
