from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from incident_investigator.ai import create_ai_runtime
from incident_investigator.config import get_settings
from incident_investigator.database.models import IncidentInvestigation
from incident_investigator.models.orchestration import OrchestratedInvestigation
from incident_investigator.repositories.investigation_repository import InvestigationRepository
from incident_investigator.services.orchestration_service import orchestrate_incident_with_usage


async def run_and_store_investigation(
    *,
    session: AsyncSession,
    incident_id: str,
    created_by_user_id: str,
    log_text: str,
    problem_description: str | None = None,
) -> tuple[IncidentInvestigation, OrchestratedInvestigation]:
    runtime = create_ai_runtime(get_settings())
    started_at = perf_counter()
    result, usage = await orchestrate_incident_with_usage(
        log_text,
        problem_description=problem_description,
        runtime=runtime,
    )
    duration_ms = round((perf_counter() - started_at) * 1000)

    repository = InvestigationRepository(session)
    stored_investigation = await repository.create(
        incident_id=incident_id,
        created_by_user_id=created_by_user_id,
        investigation=result,
        provider_name=runtime.provider.value,
        model_name=runtime.model_name,
        duration_ms=duration_ms,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        estimated_cost_usd=usage.estimated_cost_usd,
        cost_status=usage.cost_status,
        cost_currency=usage.currency,
        pricing_source=usage.pricing_source,
    )
    return stored_investigation, result
