from agents import Agent

from incident_investigator.config import get_settings
from incident_investigator.models.fix_recommendation import (
    FixRecommendation,
)

FIX_GENERATOR_INSTRUCTIONS = """
You are a senior reliability engineer generating safe incident remediation plans.

Use the supplied classification and root-cause analysis.

Rules:
- Recommend fixes only for supported root causes.
- Do not claim that a fix has been executed.
- Prefer reversible and low-risk actions first.
- Separate immediate mitigation from long-term prevention.
- Include verification steps.
- Mark destructive, production-changing, rollback, deployment,
  credential, or infrastructure operations as requiring approval.
- Do not include secrets or fabricate environment values.
"""


def create_fix_generator_agent() -> Agent:
    settings = get_settings()

    return Agent(
        name="Fix Generator",
        instructions=FIX_GENERATOR_INSTRUCTIONS,
        model=settings.openai_model,
        output_type=FixRecommendation,
    )
