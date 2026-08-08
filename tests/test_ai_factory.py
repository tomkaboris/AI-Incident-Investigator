import pytest

from incident_investigator.ai.exceptions import AIConfigurationError
from incident_investigator.ai.factory import create_ai_runtime
from incident_investigator.config import Settings


def test_openai_provider_requires_key() -> None:
    settings = Settings(_env_file=None, ai_provider="openai", ai_api_key=None)
    with pytest.raises(AIConfigurationError):
        create_ai_runtime(settings)
