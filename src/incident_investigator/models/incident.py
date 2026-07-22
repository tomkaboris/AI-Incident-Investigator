from enum import StrEnum

from pydantic import BaseModel, Field


class IncidentCategory(StrEnum):
    BUILD_FAILURE = "build_failure"
    DEPENDENCY = "dependency"
    INFRASTRUCTURE = "infrastructure"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    REGRESSION = "regression"
    UNKNOWN = "unknown"


class IncidentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Evidence(BaseModel):
    line_number: int | None = None
    excerpt: str
    explanation: str


class IncidentAnalysis(BaseModel):
    title: str
    summary: str
    category: IncidentCategory
    severity: IncidentSeverity
    probable_root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)

    evidence: list[Evidence] = Field(
        default_factory=list,
        max_length=7,
    )

    recommended_actions: list[str] = Field(
        default_factory=list,
        max_length=5,
    )

    requires_human_review: bool = True
