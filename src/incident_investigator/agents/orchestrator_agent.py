from agents import Agent

from incident_investigator.agents.classifier_agent import (
    create_classifier_agent,
)
from incident_investigator.agents.documentation_agent import (
    create_documentation_agent,
)
from incident_investigator.agents.fix_generator_agent import (
    create_fix_generator_agent,
)
from incident_investigator.agents.root_cause_agent import (
    create_root_cause_agent,
)
from incident_investigator.config import get_settings
from incident_investigator.models.orchestration import (
    OrchestratedInvestigation,
)

ORCHESTRATOR_INSTRUCTIONS = """
You are the Incident Investigation Orchestrator.

Your responsibility is to coordinate specialist agents and return one complete
incident investigation.

Required workflow:
1. Call the incident classifier.
2. Call the root-cause investigator.
3. Call the fix generator using the classification and root-cause findings.
4. Call the documentation agent using all previous findings.
5. Return the combined structured investigation.

Rules:
- Do not perform specialist analysis yourself when a specialist tool exists.
- Do not skip required specialists.
- Preserve uncertainty and missing information.
- Never claim an external action was executed.
- Ensure the final result is internally consistent.
"""


def create_orchestrator_agent() -> Agent:
    settings = get_settings()

    classifier = create_classifier_agent()
    root_cause = create_root_cause_agent()
    fix_generator = create_fix_generator_agent()
    documentation = create_documentation_agent()

    return Agent(
        name="Incident Investigation Orchestrator",
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        model=settings.openai_model,
        tools=[
            classifier.as_tool(
                tool_name="classify_incident",
                tool_description=("Classify the incident from supplied technical evidence."),
            ),
            root_cause.as_tool(
                tool_name="investigate_root_cause",
                tool_description=("Determine the probable root cause and supporting evidence."),
            ),
            fix_generator.as_tool(
                tool_name="generate_fix_plan",
                tool_description=("Generate safe remediation and prevention recommendations."),
            ),
            documentation.as_tool(
                tool_name="create_incident_report",
                tool_description=("Create a professional structured incident report."),
            ),
        ],
        output_type=OrchestratedInvestigation,
    )
