from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from incident_investigator.database.models import IncidentActivity


class ActivityRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(
        self, *, incident_id: str, user_id: str | None, action: str, details: dict | None = None
    ) -> IncidentActivity:
        row = IncidentActivity(
            incident_id=incident_id, user_id=user_id, action=action, details=details or {}
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_for_incident(self, incident_id: str):
        result = await self._session.execute(
            select(IncidentActivity)
            .options(selectinload(IncidentActivity.user))
            .where(IncidentActivity.incident_id == incident_id)
            .order_by(IncidentActivity.created_at.desc())
        )
        return result.scalars().all()
