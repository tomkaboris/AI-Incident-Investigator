from datetime import datetime

from pydantic import BaseModel, ConfigDict

from incident_investigator.models.incident import IncidentAnalysis


class IncidentCreatedResponse(BaseModel):
    id: str
    status: str
    organization_id: str
    created_by_user_id: str
    created_by_name: str | None = None
    assigned_to_user_id: str | None = None
    assigned_to_name: str | None = None
    filename: str
    problem_description: str | None = None
    created_at: datetime
    log_storage_backend: str
    log_checksum_sha256: str
    log_size_bytes: int
    log_content_type: str
    analysis: IncidentAnalysis
    initial_provider_name: str | None = None
    initial_model_name: str | None = None
    initial_input_tokens: int | None = None
    initial_output_tokens: int | None = None
    initial_total_tokens: int | None = None
    initial_estimated_cost_usd: float | None = None
    initial_cost_status: str = "usage_unavailable"
    initial_cost_currency: str = "USD"
    initial_pricing_source: str | None = None


class IncidentResponse(IncidentCreatedResponse):
    model_config = ConfigDict(from_attributes=True)
