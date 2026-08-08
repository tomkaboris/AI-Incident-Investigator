from incident_investigator.config import AIProvider, Settings


def test_legacy_openai_variables_are_supported() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="legacy-key",
        openai_model="legacy-model",
    )
    assert settings.ai_provider is AIProvider.OPENAI
    assert settings.ai_api_key == "legacy-key"
    assert settings.ai_model == "legacy-model"


def test_litellm_does_not_require_generic_api_key() -> None:
    settings = Settings(_env_file=None, ai_provider="litellm", ai_model="anthropic/test")
    assert settings.ai_api_key is None
