from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from incident_investigator.database.connection import get_database_session
from incident_investigator.database.models import MemberRole, Organization, OrganizationMember, User


@dataclass(frozen=True, slots=True)
class AuthContext:
    user: User
    organization: Organization
    membership: OrganizationMember


async def get_auth_context(
    request: Request, session: Annotated[AsyncSession, Depends(get_database_session)]
) -> AuthContext:
    user_id = request.session.get("user_id")
    organization_id = request.session.get("organization_id")
    if not user_id or not organization_id:
        raise HTTPException(status_code=401, detail="Authentication required.")
    result = await session.execute(
        select(OrganizationMember)
        .options(
            selectinload(OrganizationMember.user), selectinload(OrganizationMember.organization)
        )
        .where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None or not membership.user.is_active:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Session is no longer valid.")
    return AuthContext(membership.user, membership.organization, membership)


CurrentAuth = Annotated[AuthContext, Depends(get_auth_context)]


def require_roles(*roles: MemberRole):
    allowed = {role.value for role in roles}

    async def dependency(auth: CurrentAuth) -> AuthContext:
        if auth.membership.role not in allowed:
            raise HTTPException(
                status_code=403, detail="You do not have permission for this action."
            )
        return auth

    return dependency
