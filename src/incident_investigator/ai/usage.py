from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from incident_investigator.config import Settings


@dataclass(frozen=True, slots=True)
class AIUsageSummary:
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: Decimal | None
    cost_status: str
    pricing_source: str | None = None
    currency: str = "USD"


def _integer(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def extract_token_usage(result: Any) -> tuple[int | None, int | None, int | None]:
    wrapper = getattr(result, "context_wrapper", None)
    usage = getattr(wrapper, "usage", None)
    if usage is None:
        return None, None, None

    input_tokens = _integer(getattr(usage, "input_tokens", None))
    output_tokens = _integer(getattr(usage, "output_tokens", None))
    total_tokens = _integer(getattr(usage, "total_tokens", None))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    return input_tokens, output_tokens, total_tokens


def summarize_ai_usage(
    *,
    result: Any,
    settings: Settings,
    provider_name: str,
    model_name: str,
) -> AIUsageSummary:
    input_tokens, output_tokens, total_tokens = extract_token_usage(result)
    if input_tokens is None and output_tokens is None:
        return AIUsageSummary(
            input_tokens=None,
            output_tokens=None,
            total_tokens=total_tokens,
            estimated_cost_usd=None,
            cost_status="usage_unavailable",
        )

    pricing = settings.get_model_pricing(provider_name, model_name)
    if pricing is None:
        return AIUsageSummary(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=None,
            cost_status="pricing_unconfigured",
        )

    input_rate = Decimal(str(pricing["input_per_1m"]))
    output_rate = Decimal(str(pricing["output_per_1m"]))
    cost = (
        Decimal(input_tokens or 0) * input_rate + Decimal(output_tokens or 0) * output_rate
    ) / Decimal(1_000_000)
    cost = cost.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
    return AIUsageSummary(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=cost,
        cost_status="estimated",
        pricing_source="AI_MODEL_PRICING_JSON",
    )
