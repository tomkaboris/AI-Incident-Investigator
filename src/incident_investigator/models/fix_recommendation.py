from enum import StrEnum

from pydantic import BaseModel, Field


class FixRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FixAction(BaseModel):
    title: str
    description: str
    rationale: str

    commands: list[str] = Field(
        default_factory=list,
        max_length=5,
    )

    verification_steps: list[str] = Field(
        default_factory=list,
        max_length=5,
    )

    risk: FixRisk
    requires_approval: bool = True


class FixRecommendation(BaseModel):
    recommended_strategy: str

    immediate_actions: list[FixAction] = Field(
        default_factory=list,
        max_length=3,
    )

    long_term_actions: list[FixAction] = Field(
        default_factory=list,
        max_length=3,
    )

    rollback_recommended: bool = False
