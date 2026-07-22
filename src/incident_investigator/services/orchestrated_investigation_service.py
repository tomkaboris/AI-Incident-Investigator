from sqlalchemy.ext.asyncio import AsyncSession

from incident_investigator.config import get_settings
from incident_investigator.database.models import IncidentInvestigation
from incident_investigator.models.orchestration import OrchestratedInvestigation
from incident_investigator.repositories.investigation_repository import (
    InvestigationRepository,
)
from incident_investigator.services.orchestration_service import orchestrate_incident


async def run_and_store_investigation(
    *,
    session: AsyncSession,
    incident_id: str,
    log_text: str,
) -> tuple[IncidentInvestigation, OrchestratedInvestigation]:
    result = await orchestrate_incident(log_text)

    repository = InvestigationRepository(session)
    stored_investigation = await repository.create(
        incident_id=incident_id,
        investigation=result,
        model_name=get_settings().openai_model,
    )
    return stored_investigation, result
