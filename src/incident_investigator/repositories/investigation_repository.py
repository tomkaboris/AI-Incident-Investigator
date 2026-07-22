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
        investigation: OrchestratedInvestigation,
        model_name: str,
    ) -> IncidentInvestigation:
        record = IncidentInvestigation(
            incident_id=incident_id,
            category=investigation.classification.category.value,
            classification_confidence=investigation.classification.confidence,
            root_cause_confidence=investigation.root_cause.confidence,
            requires_human_review=investigation.root_cause.requires_human_review,
            model_name=model_name,
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
        self,
        investigation_id: int,
    ) -> IncidentInvestigation | None:
        statement = select(IncidentInvestigation).where(
            IncidentInvestigation.id == investigation_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_incident_id(
        self,
        incident_id: str,
    ) -> Sequence[IncidentInvestigation]:
        statement = (
            select(IncidentInvestigation)
            .where(IncidentInvestigation.incident_id == incident_id)
            .order_by(IncidentInvestigation.created_at.desc())
        )
        result = await self._session.execute(statement)
        return result.scalars().all()
