from dataclasses import dataclass
from typing import Any

from agents import RunConfig

from incident_investigator.config import AIProvider


@dataclass(frozen=True, slots=True)
class AIRuntime:
    provider: AIProvider
    model_name: str
    run_config: RunConfig

    async def run(self, agent: Any, input_text: str, **kwargs: Any) -> Any:
        from agents import Runner

        try:
            return await Runner.run(
                agent,
                input_text,
                run_config=self.run_config,
                **kwargs,
            )
        except Exception as exc:
            self._raise_provider_error(exc)

    @staticmethod
    def _raise_provider_error(exc: Exception) -> None:
        from incident_investigator.ai.exceptions import (
            AIAuthenticationError,
            AIProviderError,
            AIQuotaError,
            AIRateLimitError,
        )

        if isinstance(exc, AIProviderError):
            raise exc

        class_name = type(exc).__name__.lower()
        message = str(exc).lower()

        if "authentication" in class_name or "api key" in message or "unauthorized" in message:
            raise AIAuthenticationError(str(exc)) from exc
        if "insufficient_quota" in message or "quota" in class_name:
            raise AIQuotaError(str(exc)) from exc
        if "ratelimit" in class_name or "rate limit" in message or "too many requests" in message:
            raise AIRateLimitError(str(exc)) from exc
        raise AIProviderError(str(exc)) from exc
