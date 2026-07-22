from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from incident_investigator.database.models import IncidentRecord
from incident_investigator.models.incident import IncidentAnalysis


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        filename: str,
        raw_log: str,
        analysis: IncidentAnalysis,
    ) -> IncidentRecord:
        record = IncidentRecord(
            filename=filename,
            raw_log=raw_log,
            title=analysis.title,
            category=str(analysis.category),
            severity=str(analysis.severity),
            summary=analysis.summary,
            probable_root_cause=analysis.probable_root_cause,
            confidence=analysis.confidence,
            analysis=analysis.model_dump(mode="json"),
        )

        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)

        return record

    async def get_by_id(
        self,
        incident_id: str,
    ) -> IncidentRecord | None:
        statement = select(IncidentRecord).where(IncidentRecord.id == incident_id)

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
