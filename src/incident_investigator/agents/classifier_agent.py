from agents import Agent

from incident_investigator.config import get_settings
from incident_investigator.models.classification import (
    IncidentClassification,
)

CLASSIFIER_INSTRUCTIONS = """
You are an incident classification specialist.

Classify the provided incident data into one primary category.

Allowed categories:
- infrastructure
- network
- build_failure
- dependency
- memory_leak
- timeout
- authentication
- regression
- unknown

Rules:
- Base the classification only on the supplied evidence.
- Do not invent information.
- Distinguish the primary failure from downstream symptoms.
- Include no more than three secondary categories.
- Return short indicators supporting the classification.
- Use unknown when evidence is insufficient.
"""


def create_classifier_agent() -> Agent:
    settings = get_settings()

    return Agent(
        name="Incident Classifier",
        instructions=CLASSIFIER_INSTRUCTIONS,
        model=settings.openai_model,
        output_type=IncidentClassification,
    )
