from agents import Runner

from incident_investigator.agents.orchestrator_agent import (
    create_orchestrator_agent,
)
from incident_investigator.config import get_settings
from incident_investigator.models.orchestration import (
    OrchestratedInvestigation,
)


async def orchestrate_incident(
    log_text: str,
) -> OrchestratedInvestigation:
    """Run the multi-agent incident investigation workflow."""

    settings = get_settings()

    prepared_log = log_text[: settings.max_log_characters]

    input_text = f"""
Investigate the following incident.

Available evidence:
- Uploaded CI/CD log

Unavailable evidence:
- Git diff
- Git commit history
- Docker logs
- Kubernetes events
- Prometheus metrics
- Slack discussion

CI/CD LOG:

{prepared_log}
"""

    orchestrator = create_orchestrator_agent()

    result = await Runner.run(
        orchestrator,
        input_text,
        max_turns=12,
    )

    final_output = result.final_output

    if not isinstance(final_output, OrchestratedInvestigation):
        raise TypeError(
            f"Orchestrator returned an unexpected output type: {type(final_output).__name__}"
        )

    return final_output
