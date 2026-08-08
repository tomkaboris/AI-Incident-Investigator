"""Lazy exports for AI runtime integrations.

Keeping imports lazy allows configuration and cost utilities to be used without
loading optional provider SDK components during test collection.
"""

from typing import Any

__all__ = [
    "AIRuntime",
    "AIUsageSummary",
    "create_ai_runtime",
    "summarize_ai_usage",
]


def __getattr__(name: str) -> Any:
    if name == "create_ai_runtime":
        from incident_investigator.ai.factory import create_ai_runtime

        return create_ai_runtime
    if name == "AIRuntime":
        from incident_investigator.ai.runtime import AIRuntime

        return AIRuntime
    if name in {"AIUsageSummary", "summarize_ai_usage"}:
        from incident_investigator.ai.usage import AIUsageSummary, summarize_ai_usage

        return {
            "AIUsageSummary": AIUsageSummary,
            "summarize_ai_usage": summarize_ai_usage,
        }[name]
    raise AttributeError(name)
