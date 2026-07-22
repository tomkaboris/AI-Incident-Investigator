from pydantic import BaseModel, Field


class RootCauseEvidence(BaseModel):
    source: str
    line_number: int | None = None
    excerpt: str
    explanation: str


class RootCauseAnalysis(BaseModel):
    probable_root_cause: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    failure_chain: list[str] = Field(
        default_factory=list,
        max_length=8,
    )

    evidence: list[RootCauseEvidence] = Field(
        default_factory=list,
        max_length=7,
    )

    contributing_factors: list[str] = Field(
        default_factory=list,
        max_length=5,
    )

    missing_information: list[str] = Field(
        default_factory=list,
        max_length=5,
    )

    requires_human_review: bool = True
