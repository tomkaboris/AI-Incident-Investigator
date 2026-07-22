from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from incident_investigator.models.orchestration import OrchestratedInvestigation


class InvestigationStoredResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: str
    category: str
    classification_confidence: float
    root_cause_confidence: float
    requires_human_review: bool
    model_name: str
    full_result: dict[str, Any]
    created_at: datetime


class OrchestrationResponse(BaseModel):
    investigation_id: int
    incident_id: str
    model_name: str
    created_at: datetime
    result: OrchestratedInvestigation
