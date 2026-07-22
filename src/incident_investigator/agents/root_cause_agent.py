from agents import Agent

from incident_investigator.config import get_settings
from incident_investigator.models.root_cause import RootCauseAnalysis

ROOT_CAUSE_INSTRUCTIONS = """
You are a senior Site Reliability Engineer specializing in root-cause analysis.

Analyze the incident data and identify the most probable root cause.

Rules:
- Separate the root cause from downstream consequences.
- Cite exact evidence from the supplied data.
- Never invent logs, commits, metrics, events, or timestamps.
- Explain the causal chain leading to the final failure.
- Explicitly list important missing information.
- Reduce confidence when required evidence is unavailable.
- Return no more than seven evidence items.
- Mark the result for human review when confidence is below 0.85,
  when evidence conflicts, or when a proposed conclusion requires assumptions.
"""


def create_root_cause_agent() -> Agent:
    settings = get_settings()

    return Agent(
        name="Root Cause Investigator",
        instructions=ROOT_CAUSE_INSTRUCTIONS,
        model=settings.openai_model,
        output_type=RootCauseAnalysis,
    )
