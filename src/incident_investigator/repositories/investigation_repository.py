from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from incident_investigator.database.models import IncidentInvestigation
from incident_investigator.models.orchestration import OrchestratedInvestigation


class InvestigationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        incident_id: str,
        created_by_user_id: str,
        investigation: OrchestratedInvestigation,
        provider_name: str,
        model_name: str,
        prompt_version: str = "v1",
        duration_ms: int | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
        estimated_cost_usd=None,
        cost_status: str = "usage_unavailable",
        cost_currency: str = "USD",
        pricing_source: str | None = None,
    ) -> IncidentInvestigation:
        record = IncidentInvestigation(
            incident_id=incident_id,
            created_by_user_id=created_by_user_id,
            category=investigation.classification.category.value,
            classification_confidence=investigation.classification.confidence,
            root_cause_confidence=investigation.root_cause.confidence,
            requires_human_review=investigation.root_cause.requires_human_review,
            provider_name=provider_name,
            model_name=model_name,
            prompt_version=prompt_version,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            cost_status=cost_status,
            cost_currency=cost_currency,
            pricing_source=pricing_source,
            classification=investigation.classification.model_dump(mode="json"),
            root_cause=investigation.root_cause.model_dump(mode="json"),
            fix_recommendation=investigation.fix_recommendation.model_dump(mode="json"),
            report=investigation.report.model_dump(mode="json"),
            full_result=investigation.model_dump(mode="json"),
        )
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def get_by_id(
        self, investigation_id: int, organization_id: str
    ) -> IncidentInvestigation | None:
        from incident_investigator.database.models import IncidentRecord

        result = await self._session.execute(
            select(IncidentInvestigation)
            .join(IncidentRecord, IncidentRecord.id == IncidentInvestigation.incident_id)
            .where(
                IncidentInvestigation.id == investigation_id,
                IncidentRecord.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_incident_id(
        self, incident_id: str, organization_id: str
    ) -> Sequence[IncidentInvestigation]:
        from incident_investigator.database.models import IncidentRecord

        result = await self._session.execute(
            select(IncidentInvestigation)
            .join(IncidentRecord, IncidentRecord.id == IncidentInvestigation.incident_id)
            .where(
                IncidentInvestigation.incident_id == incident_id,
                IncidentRecord.organization_id == organization_id,
            )
            .order_by(IncidentInvestigation.created_at.desc())
        )
        return result.scalars().all()
