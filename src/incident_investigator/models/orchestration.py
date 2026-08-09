from pydantic import BaseModel
from pydantic.json_schema import SkipJsonSchema

from incident_investigator.models.classification import (
    IncidentClassification,
)
from incident_investigator.models.fix_recommendation import (
    FixRecommendation,
)
from incident_investigator.models.incident_report import IncidentReport
from incident_investigator.models.root_cause import RootCauseAnalysis
from incident_investigator.source_analysis.models import SourceAnalysis


class OrchestratedInvestigation(BaseModel):
    classification: IncidentClassification
    root_cause: RootCauseAnalysis
    fix_recommendation: FixRecommendation
    report: IncidentReport
    source_analysis: SkipJsonSchema[SourceAnalysis | None] = None
