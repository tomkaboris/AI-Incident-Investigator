from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from incident_investigator.models.orchestration import OrchestratedInvestigation


class InvestigationStoredResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: str
    created_by_user_id: str
    category: str
    classification_confidence: float
    root_cause_confidence: float
    requires_human_review: bool
    provider_name: str
    model_name: str
    prompt_version: str
    duration_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None
    cost_status: str
    cost_currency: str
    pricing_source: str | None
    full_result: dict[str, Any]
    created_at: datetime


class OrchestrationResponse(BaseModel):
    investigation_id: int
    incident_id: str
    provider_name: str
    model_name: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    cost_status: str = "usage_unavailable"
    cost_currency: str = "USD"
    pricing_source: str | None = None
    created_at: datetime
    result: OrchestratedInvestigation
