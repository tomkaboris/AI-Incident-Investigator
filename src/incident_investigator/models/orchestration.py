from pydantic import BaseModel

from incident_investigator.models.classification import (
    IncidentClassification,
)
from incident_investigator.models.fix_recommendation import (
    FixRecommendation,
)
from incident_investigator.models.incident_report import IncidentReport
from incident_investigator.models.root_cause import RootCauseAnalysis


class OrchestratedInvestigation(BaseModel):
    classification: IncidentClassification
    root_cause: RootCauseAnalysis
    fix_recommendation: FixRecommendation
    report: IncidentReport
