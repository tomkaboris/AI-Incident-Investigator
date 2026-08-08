from enum import StrEnum

from pydantic import BaseModel, Field


class IncidentCategory(StrEnum):
    INFRASTRUCTURE = "infrastructure"
    NETWORK = "network"
    BUILD_FAILURE = "build_failure"
    DEPENDENCY = "dependency"
    MEMORY_LEAK = "memory_leak"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    REGRESSION = "regression"
    UNKNOWN = "unknown"


class IncidentClassification(BaseModel):
    category: IncidentCategory

    secondary_categories: list[IncidentCategory] = Field(
        default_factory=list,
        max_length=3,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    reasoning: str

    indicators: list[str] = Field(
        default_factory=list,
        max_length=5,
    )
