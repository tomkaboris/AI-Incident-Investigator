from agents import Agent

from incident_investigator.config import get_settings
from incident_investigator.models.incident_report import IncidentReport

DOCUMENTATION_INSTRUCTIONS = """
You are a technical incident documentation specialist.

Create a professional incident report using only the supplied investigation.

The report must contain:
- title
- executive summary
- impact
- timeline
- root cause
- resolution or proposed resolution
- preventive actions
- complete Markdown version

Rules:
- Do not add facts that are not present.
- Clearly distinguish confirmed facts from probable conclusions.
- Do not claim that proposed fixes were executed.
- Make the Markdown suitable for a GitHub Issue or Confluence page.
"""


def create_documentation_agent() -> Agent:
    settings = get_settings()

    return Agent(
        name="Incident Documentation",
        instructions=DOCUMENTATION_INSTRUCTIONS,
        model=settings.openai_model,
        output_type=IncidentReport,
    )
