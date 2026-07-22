from datetime import datetime

from pydantic import BaseModel, ConfigDict

from incident_investigator.models.incident import IncidentAnalysis


class IncidentCreatedResponse(BaseModel):
    id: str
    status: str
    filename: str
    created_at: datetime
    analysis: IncidentAnalysis


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    filename: str
    created_at: datetime
    analysis: IncidentAnalysis
