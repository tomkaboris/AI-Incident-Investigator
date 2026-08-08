from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from incident_investigator.auth.context import CurrentAuth
from incident_investigator.database.connection import get_database_session
from incident_investigator.database.models import MemberRole, User
from incident_investigator.repositories.activity_repository import ActivityRepository
from incident_investigator.repositories.incident_repository import IncidentRepository

router = APIRouter(prefix="/api/v1/incidents", tags=["collaboration"])


class AssignRequest(BaseModel):
    assigned_to_user_id: str | None


class StatusRequest(BaseModel):
    status: str


@router.get("/{incident_id}/activities")
async def activities(
    incident_id: str,
    auth: CurrentAuth,
    session: Annotated[AsyncSession, Depends(get_database_session)],
):
    incident = await IncidentRepository(session).get_by_id(incident_id, auth.organization.id)
    if not incident:
        raise HTTPException(404, "Incident not found.")
    rows = await ActivityRepository(session).list_for_incident(incident_id)
    return [
        {
            "id": r.id,
            "action": r.action,
            "details": r.details,
            "created_at": r.created_at,
            "user_id": r.user_id,
            "user_name": r.user.full_name if r.user else "System",
        }
        for r in rows
    ]


@router.patch("/{incident_id}/assignment")
async def assign(
    incident_id: str,
    payload: AssignRequest,
    auth: CurrentAuth,
    session: Annotated[AsyncSession, Depends(get_database_session)],
):
    if auth.membership.role == MemberRole.VIEWER.value:
        raise HTTPException(403, "Viewer cannot assign incidents.")
    incident = await IncidentRepository(session).get_by_id(incident_id, auth.organization.id)
    if not incident:
        raise HTTPException(404, "Incident not found.")
    if payload.assigned_to_user_id and await session.get(User, payload.assigned_to_user_id) is None:
        raise HTTPException(
            status_code=400,
            detail="Unknown assignee.",
        )
    incident.assigned_to_user_id = payload.assigned_to_user_id
    await ActivityRepository(session).add(
        incident_id=incident.id,
        user_id=auth.user.id,
        action="incident_assigned",
        details={"assigned_to_user_id": payload.assigned_to_user_id},
    )
    await session.commit()
    return {"status": "updated"}


@router.patch("/{incident_id}/status")
async def update_status(
    incident_id: str,
    payload: StatusRequest,
    auth: CurrentAuth,
    session: Annotated[AsyncSession, Depends(get_database_session)],
):
    if auth.membership.role == MemberRole.VIEWER.value:
        raise HTTPException(403, "Viewer cannot update incidents.")
    if payload.status not in {"analyzed", "investigating", "resolved", "closed"}:
        raise HTTPException(400, "Unsupported status.")
    incident = await IncidentRepository(session).get_by_id(incident_id, auth.organization.id)
    if not incident:
        raise HTTPException(404, "Incident not found.")
    incident.status = payload.status
    await ActivityRepository(session).add(
        incident_id=incident.id,
        user_id=auth.user.id,
        action="status_changed",
        details={"status": payload.status},
    )
    await session.commit()
    return {"status": payload.status}
