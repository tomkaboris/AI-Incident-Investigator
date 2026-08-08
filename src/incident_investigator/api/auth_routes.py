from datetime import UTC, datetime
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from incident_investigator.auth.context import CurrentAuth
from incident_investigator.auth.security import (
    hash_password,
    new_csrf_token,
    normalize_email,
    slugify,
    verify_password,
)
from incident_investigator.config import get_settings
from incident_investigator.database.connection import get_database_session
from incident_investigator.database.models import MemberRole, Organization, OrganizationMember, User
from incident_investigator.models.auth import (
    AddTeamMemberRequest,
    LoginRequest,
    RegisterRequest,
    TeamMemberResponse,
    UserProfile,
)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
_login_attempts: dict[str, list[float]] = {}


def profile(auth: CurrentAuth) -> UserProfile:
    return UserProfile(
        id=auth.user.id,
        email=auth.user.email,
        full_name=auth.user.full_name,
        role=auth.membership.role,
        organization_id=auth.organization.id,
        organization_name=auth.organization.name,
        onboarding_completed=auth.user.onboarding_completed,
        created_at=auth.user.created_at,
    )


@router.post("/register", response_model=UserProfile, status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> UserProfile:
    if not get_settings().registration_enabled:
        raise HTTPException(403, "Registration is disabled.")
    email = normalize_email(str(payload.email))
    if await session.scalar(select(func.count(User.id)).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists.")
    base = slugify(payload.organization_name)
    slug = base
    suffix = 2
    while await session.scalar(
        select(func.count(Organization.id)).where(Organization.slug == slug)
    ):
        slug = f"{base}-{suffix}"
        suffix += 1
    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        is_verified=True,
    )
    org = Organization(name=payload.organization_name.strip(), slug=slug)
    session.add_all([user, org])
    await session.flush()
    member = OrganizationMember(
        user_id=user.id, organization_id=org.id, role=MemberRole.OWNER.value
    )
    session.add(member)
    await session.commit()
    request.session.clear()
    request.session.update(
        {"user_id": user.id, "organization_id": org.id, "csrf_token": new_csrf_token()}
    )
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        organization_id=org.id,
        organization_name=org.name,
        onboarding_completed=False,
        created_at=user.created_at,
    )


@router.post("/login", response_model=UserProfile)
async def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> UserProfile:
    client_key = request.client.host if request.client else "unknown"
    now = monotonic()
    attempts = [stamp for stamp in _login_attempts.get(client_key, []) if now - stamp < 300]
    if len(attempts) >= 8:
        raise HTTPException(429, "Too many login attempts. Try again later.")
    email = normalize_email(str(payload.email))
    user = await session.scalar(select(User).where(User.email == email))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        attempts.append(now)
        _login_attempts[client_key] = attempts
        raise HTTPException(401, "Invalid email or password.")
    _login_attempts.pop(client_key, None)
    member = await session.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.id)
    )
    if member is None:
        raise HTTPException(403, "User does not belong to a workspace.")
    org = await session.get(Organization, member.organization_id)
    user.last_login_at = datetime.now(UTC)
    await session.commit()
    request.session.clear()
    request.session.update(
        {"user_id": user.id, "organization_id": org.id, "csrf_token": new_csrf_token()}
    )
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        organization_id=org.id,
        organization_name=org.name,
        onboarding_completed=user.onboarding_completed,
        created_at=user.created_at,
    )


@router.post("/logout", status_code=204)
async def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=204)


@router.get("/me", response_model=UserProfile)
async def me(auth: CurrentAuth) -> UserProfile:
    return profile(auth)


@router.post("/onboarding/complete", response_model=UserProfile)
async def complete_onboarding(
    auth: CurrentAuth, session: Annotated[AsyncSession, Depends(get_database_session)]
) -> UserProfile:
    auth.user.onboarding_completed = True
    await session.commit()
    return profile(auth)


@router.get("/team", response_model=list[TeamMemberResponse])
async def team(
    auth: CurrentAuth, session: Annotated[AsyncSession, Depends(get_database_session)]
) -> list[TeamMemberResponse]:
    rows = (
        await session.execute(
            select(OrganizationMember, User)
            .join(User, User.id == OrganizationMember.user_id)
            .where(OrganizationMember.organization_id == auth.organization.id)
            .order_by(User.full_name)
        )
    ).all()
    return [
        TeamMemberResponse(
            id=u.id, email=u.email, full_name=u.full_name, role=m.role, joined_at=m.joined_at
        )
        for m, u in rows
    ]


@router.get("/csrf")
async def csrf(request: Request, auth: CurrentAuth) -> dict[str, str]:
    token = request.session.get("csrf_token")
    if not token:
        token = new_csrf_token()
        request.session["csrf_token"] = token
    return {"csrf_token": token}


@router.post("/team", response_model=TeamMemberResponse, status_code=201)
async def add_team_member(
    payload: AddTeamMemberRequest,
    auth: CurrentAuth,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> TeamMemberResponse:
    if auth.membership.role not in {MemberRole.OWNER.value, MemberRole.ADMIN.value}:
        raise HTTPException(403, "Only owners and admins can add team members.")
    if payload.role not in {role.value for role in MemberRole}:
        raise HTTPException(400, "Unsupported role.")
    if payload.role == MemberRole.OWNER.value and auth.membership.role != MemberRole.OWNER.value:
        raise HTTPException(403, "Only an owner can create another owner.")
    email = normalize_email(str(payload.email))
    if await session.scalar(select(func.count(User.id)).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists.")
    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.temporary_password),
        is_verified=True,
    )
    session.add(user)
    await session.flush()
    member = OrganizationMember(
        organization_id=auth.organization.id, user_id=user.id, role=payload.role
    )
    session.add(member)
    await session.commit()
    return TeamMemberResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        joined_at=member.joined_at,
    )
