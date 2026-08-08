from agents import RunConfig, set_default_openai_key, set_tracing_disabled

from incident_investigator.ai.exceptions import AIConfigurationError
from incident_investigator.ai.runtime import AIRuntime
from incident_investigator.config import AIProvider, Settings


def create_ai_runtime(settings: Settings) -> AIRuntime:
    if settings.ai_provider is AIProvider.OPENAI:
        if not settings.ai_api_key:
            raise AIConfigurationError(
                "AI_API_KEY is required when AI_PROVIDER=openai. "
                "OPENAI_API_KEY is still accepted for backward compatibility."
            )
        set_default_openai_key(settings.ai_api_key)
        return AIRuntime(
            provider=settings.ai_provider,
            model_name=settings.ai_model,
            run_config=RunConfig(model=settings.ai_model),
        )

    if settings.ai_provider is AIProvider.LITELLM:
        try:
            from agents.extensions.models.litellm_provider import LitellmProvider
        except ImportError as exc:
            raise AIConfigurationError(
                'LiteLLM support is not installed. Install "ai-incident-investigator[litellm]".'
            ) from exc

        # Non-OpenAI providers cannot write OpenAI traces unless tracing credentials are configured.
        set_tracing_disabled(True)
        return AIRuntime(
            provider=settings.ai_provider,
            model_name=settings.ai_model,
            run_config=RunConfig(
                model=settings.ai_model,
                model_provider=LitellmProvider(),
            ),
        )

    raise AIConfigurationError(f"Unsupported AI provider: {settings.ai_provider}")
