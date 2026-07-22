from agents import Runner

from incident_investigator.agents.incident_analyzer import (
    create_incident_analyzer,
)
from incident_investigator.config import get_settings
from incident_investigator.models.incident import IncidentAnalysis
from incident_investigator.services.log_parser import parse_log


async def investigate_log(raw_log: str) -> IncidentAnalysis:
    settings = get_settings()

    parsed_log = parse_log(
        content=raw_log,
        max_characters=settings.max_log_characters,
    )

    prompt = f"""
Analyze the following incident log.

Log metadata:
- Original lines: {parsed_log.original_line_count}
- Retained lines: {parsed_log.retained_line_count}
- Truncated: {parsed_log.truncated}

LOG START
{parsed_log.content}
LOG END
"""

    agent = create_incident_analyzer()
    result = await Runner.run(agent, prompt)

    if not isinstance(result.final_output, IncidentAnalysis):
        raise TypeError("Agent returned an unexpected output type.")

    return result.final_output
