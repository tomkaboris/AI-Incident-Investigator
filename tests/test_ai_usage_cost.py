from types import SimpleNamespace

from incident_investigator.ai.usage import summarize_ai_usage
from incident_investigator.config import Settings


def result_with_usage(input_tokens=1000, output_tokens=500):
    usage = SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )
    return SimpleNamespace(context_wrapper=SimpleNamespace(usage=usage))


def test_cost_is_calculated_from_configured_model_rates() -> None:
    settings = Settings(
        _env_file=None,
        ai_model_pricing_json=('{"openai:test-model":{"input_per_1m":2,"output_per_1m":8}}'),
    )
    summary = summarize_ai_usage(
        result=result_with_usage(),
        settings=settings,
        provider_name="openai",
        model_name="test-model",
    )
    assert str(summary.estimated_cost_usd) == "0.00600000"
    assert summary.cost_status == "estimated"


def test_missing_price_does_not_invent_cost() -> None:
    settings = Settings(_env_file=None, ai_model_pricing_json="{}")
    summary = summarize_ai_usage(
        result=result_with_usage(),
        settings=settings,
        provider_name="openai",
        model_name="unknown",
    )
    assert summary.estimated_cost_usd is None
    assert summary.cost_status == "pricing_unconfigured"
