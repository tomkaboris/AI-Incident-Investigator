from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from incident_investigator.auth.context import CurrentAuth, get_auth_context
from incident_investigator.database.connection import get_database_session
from incident_investigator.database.models import IncidentInvestigation, IncidentRecord, User
from incident_investigator.models.dashboard import DashboardOverview, IncidentListItem

router = APIRouter(
    prefix="/api/v1/dashboard", tags=["dashboard"], dependencies=[Depends(get_auth_context)]
)


def _item(record, count, confidence, review, creator_name, assignee_name):
    return IncidentListItem(
        id=record.id,
        title=record.title,
        status=record.status,
        filename=record.filename,
        problem_description=record.problem_description,
        category=record.category,
        severity=record.severity,
        summary=record.summary,
        probable_root_cause=record.probable_root_cause,
        confidence=record.confidence,
        log_storage_backend=record.log_storage_backend,
        log_size_bytes=record.log_size_bytes,
        created_at=record.created_at,
        investigation_count=int(count or 0),
        latest_root_cause_confidence=confidence,
        requires_human_review=bool(review),
        created_by_name=creator_name,
        assigned_to_name=assignee_name,
    )


@router.get("/incidents", response_model=list[IncidentListItem])
async def list_dashboard_incidents(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
    search: Annotated[str | None, Query(max_length=200)] = None,
    severity: str | None = None,
    category: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
):
    counts = (
        select(
            IncidentInvestigation.incident_id.label("incident_id"),
            func.count(IncidentInvestigation.id).label("investigation_count"),
        )
        .group_by(IncidentInvestigation.incident_id)
        .subquery()
    )
    latest_id = (
        select(func.max(IncidentInvestigation.id))
        .where(IncidentInvestigation.incident_id == IncidentRecord.id)
        .correlate(IncidentRecord)
        .scalar_subquery()
    )
    latest = aliased(IncidentInvestigation)
    creator = aliased(User)
    assignee = aliased(User)
    statement = (
        select(
            IncidentRecord,
            func.coalesce(counts.c.investigation_count, 0),
            latest.root_cause_confidence,
            latest.requires_human_review,
            creator.full_name,
            assignee.full_name,
        )
        .outerjoin(counts, counts.c.incident_id == IncidentRecord.id)
        .outerjoin(latest, latest.id == latest_id)
        .join(creator, creator.id == IncidentRecord.created_by_user_id)
        .outerjoin(assignee, assignee.id == IncidentRecord.assigned_to_user_id)
        .where(IncidentRecord.organization_id == auth.organization.id)
        .order_by(IncidentRecord.created_at.desc())
        .limit(limit)
    )
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            IncidentRecord.title.ilike(pattern)
            | IncidentRecord.filename.ilike(pattern)
            | IncidentRecord.summary.ilike(pattern)
            | IncidentRecord.problem_description.ilike(pattern)
            | creator.full_name.ilike(pattern)
        )
    if severity:
        statement = statement.where(IncidentRecord.severity == severity)
    if category:
        statement = statement.where(IncidentRecord.category == category)
    return [_item(*row) for row in (await session.execute(statement)).all()]


@router.get("/overview", response_model=DashboardOverview)
async def dashboard_overview(
    session: Annotated[AsyncSession, Depends(get_database_session)], auth: CurrentAuth
):
    org_filter = IncidentRecord.organization_id == auth.organization.id
    incident_stats = (
        await session.execute(
            select(
                func.count(IncidentRecord.id),
                func.sum(case((IncidentRecord.status != "resolved", 1), else_=0)),
                func.sum(case((IncidentRecord.severity == "critical", 1), else_=0)),
                func.avg(IncidentRecord.confidence),
                func.coalesce(func.sum(IncidentRecord.log_size_bytes), 0),
            ).where(org_filter)
        )
    ).one()
    investigation_stats = (
        await session.execute(
            select(
                func.count(IncidentInvestigation.id),
                func.sum(case((IncidentInvestigation.requires_human_review.is_(True), 1), else_=0)),
                func.avg(IncidentInvestigation.duration_ms),
            )
            .join(IncidentRecord, IncidentRecord.id == IncidentInvestigation.incident_id)
            .where(org_filter)
        )
    ).one()
    severity_rows = (
        await session.execute(
            select(IncidentRecord.severity, func.count(IncidentRecord.id))
            .where(org_filter)
            .group_by(IncidentRecord.severity)
        )
    ).all()
    category_rows = (
        await session.execute(
            select(IncidentRecord.category, func.count(IncidentRecord.id))
            .where(org_filter)
            .group_by(IncidentRecord.category)
        )
    ).all()
    recent = await list_dashboard_incidents(session=session, auth=auth, limit=8)
    return DashboardOverview(
        total_incidents=int(incident_stats[0] or 0),
        open_incidents=int(incident_stats[1] or 0),
        critical_incidents=int(incident_stats[2] or 0),
        investigations_total=int(investigation_stats[0] or 0),
        human_review_required=int(investigation_stats[1] or 0),
        average_confidence=round(float(incident_stats[3] or 0), 4),
        average_analysis_duration_ms=round(float(investigation_stats[2]), 2)
        if investigation_stats[2] is not None
        else None,
        storage_bytes=int(incident_stats[4] or 0),
        incidents_by_severity={str(n): int(c) for n, c in severity_rows},
        incidents_by_category={str(n): int(c) for n, c in category_rows},
        recent_incidents=recent,
    )
