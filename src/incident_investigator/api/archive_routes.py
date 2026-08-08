from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from incident_investigator.ai.exceptions import AIProviderError
from incident_investigator.api.routes import CurrentAuth
from incident_investigator.archive.detector import is_archive_path
from incident_investigator.archive.exceptions import ArchiveProcessingError
from incident_investigator.config import get_settings
from incident_investigator.database.connection import get_database_session
from incident_investigator.database.models import (
    IncidentArchive,
    IncidentArtifact,
    IncidentLogEvent,
    MemberRole,
)
from incident_investigator.models.archive import (
    ArchiveAnalysisStoredResponse,
    ArchiveCreatedResponse,
    ArtifactResponse,
    TimelineEventResponse,
)
from incident_investigator.repositories.activity_repository import ActivityRepository
from incident_investigator.repositories.incident_repository import IncidentRepository
from incident_investigator.services.archive_investigation_service import analyze_archive
from incident_investigator.storage import get_log_storage
from incident_investigator.storage.exceptions import LogStorageError

router = APIRouter(prefix="/api/v1/incidents", tags=["archive investigations"])


@router.post("/analyze-archive", response_model=ArchiveCreatedResponse, status_code=201)
async def analyze_archive_upload(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
    archive_file: Annotated[UploadFile, File()],
    problem_description: Annotated[str, Form(min_length=3, max_length=5000)],
    incident_time: Annotated[datetime | None, Form()] = None,
    timezone: Annotated[str, Form()] = "UTC",
    system_name: Annotated[str | None, Form()] = None,
):
    if auth.membership.role == MemberRole.VIEWER.value:
        raise HTTPException(403, "Viewer cannot create incidents.")
    settings = get_settings()
    content = await archive_file.read()
    if not content:
        raise HTTPException(400, "Uploaded archive is empty.")
    if len(content) > settings.max_archive_upload_size_bytes:
        raise HTTPException(413, "Archive exceeds the configured upload limit.")
    filename = archive_file.filename or "support-bundle.zip"
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(400, "Unknown timezone.") from exc
    from pathlib import Path

    if not is_archive_path(Path(filename)):
        raise HTTPException(400, "Unsupported archive extension.")
    try:
        record, archive, analysis = await analyze_archive(
            session=session,
            organization_id=auth.organization.id,
            user_id=auth.user.id,
            filename=filename,
            content=content,
            content_type=archive_file.content_type or "application/octet-stream",
            problem_description=problem_description,
            incident_time=incident_time,
            timezone_name=timezone,
            system_name=system_name,
        )
        await ActivityRepository(session).add(
            incident_id=record.id,
            user_id=auth.user.id,
            action="archive_incident_created",
            details={"archive_id": archive.id, "artifact_count": archive.artifact_count},
        )
        await session.commit()
        await session.refresh(archive)
        return ArchiveCreatedResponse(
            incident_id=record.id,
            archive_id=archive.id,
            status=archive.status,
            uploaded_filename=archive.uploaded_filename,
            problem_description=archive.problem_description,
            incident_time=archive.incident_time,
            timezone=archive.timezone,
            system_name=archive.system_name,
            artifact_count=archive.artifact_count,
            total_extracted_size_bytes=archive.total_extracted_size_bytes,
            max_depth_reached=archive.max_depth_reached,
            analysis=analysis,
            provider_name=archive.provider_name,
            model_name=archive.model_name,
            input_tokens=archive.input_tokens,
            output_tokens=archive.output_tokens,
            total_tokens=archive.total_tokens,
            estimated_cost_usd=archive.estimated_cost_usd,
            cost_status=archive.cost_status,
            cost_currency=archive.cost_currency,
            pricing_source=archive.pricing_source,
        )
    except ArchiveProcessingError as exc:
        raise HTTPException(400, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except AIProviderError as exc:
        raise HTTPException(502, "AI provider request failed.") from exc
    except LogStorageError as exc:
        raise HTTPException(503, "Log storage is unavailable.") from exc


async def _get_incident(session, auth, incident_id):
    incident = await IncidentRepository(session).get_by_id(incident_id, auth.organization.id)
    if incident is None:
        raise HTTPException(404, "Incident not found.")
    return incident


@router.get("/{incident_id}/artifacts", response_model=list[ArtifactResponse])
async def list_artifacts(
    incident_id: str,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
):
    await _get_incident(session, auth, incident_id)
    rows = (
        (
            await session.execute(
                select(IncidentArtifact)
                .where(IncidentArtifact.incident_id == incident_id)
                .order_by(IncidentArtifact.original_path)
            )
        )
        .scalars()
        .all()
    )
    return [ArtifactResponse.model_validate(row, from_attributes=True) for row in rows]


@router.get("/{incident_id}/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    incident_id: str,
    artifact_id: int,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
):
    await _get_incident(session, auth, incident_id)
    row = (
        await session.execute(
            select(IncidentArtifact).where(
                IncidentArtifact.id == artifact_id, IncidentArtifact.incident_id == incident_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Artifact not found.")
    return ArtifactResponse.model_validate(row, from_attributes=True)


@router.get("/{incident_id}/artifacts/{artifact_id}/content")
async def download_artifact(
    incident_id: str,
    artifact_id: int,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
):
    settings = get_settings()
    if not settings.allow_raw_artifact_download:
        raise HTTPException(403, "Raw artifact download is disabled.")
    await _get_incident(session, auth, incident_id)
    row = (
        await session.execute(
            select(IncidentArtifact).where(
                IncidentArtifact.id == artifact_id, IncidentArtifact.incident_id == incident_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Artifact not found.")
    content = await get_log_storage().read(key=row.storage_key)
    return Response(
        content=content,
        media_type=row.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{row.filename}"'},
    )


@router.get("/{incident_id}/timeline", response_model=list[TimelineEventResponse])
async def timeline(
    incident_id: str,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
):
    await _get_incident(session, auth, incident_id)
    stmt = (
        select(IncidentLogEvent, IncidentArtifact.original_path)
        .join(IncidentArtifact, IncidentArtifact.id == IncidentLogEvent.artifact_id)
        .where(IncidentLogEvent.incident_id == incident_id)
        .order_by(IncidentLogEvent.timestamp_utc, IncidentLogEvent.id)
        .limit(5000)
    )
    rows = (await session.execute(stmt)).all()
    return [
        TimelineEventResponse(
            artifact_id=e.artifact_id,
            path=path,
            component=e.component,
            timestamp_utc=e.timestamp_utc,
            original_timestamp=e.original_timestamp,
            severity=e.severity,
            message=e.message,
            line_number=e.line_number,
            correlation_ids=e.correlation_ids,
        )
        for e, path in rows
    ]


@router.get("/{incident_id}/archive-analysis", response_model=ArchiveAnalysisStoredResponse)
async def archive_analysis(
    incident_id: str,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
):
    await _get_incident(session, auth, incident_id)
    row = (
        (
            await session.execute(
                select(IncidentArchive)
                .where(IncidentArchive.incident_id == incident_id)
                .order_by(IncidentArchive.id.desc())
            )
        )
        .scalars()
        .first()
    )
    if row is None:
        raise HTTPException(404, "Archive analysis not found.")
    return ArchiveAnalysisStoredResponse(
        incident_id=incident_id,
        archive_id=row.id,
        uploaded_filename=row.uploaded_filename,
        incident_time=row.incident_time,
        timezone=row.timezone,
        system_name=row.system_name,
        artifact_count=row.artifact_count,
        total_extracted_size_bytes=row.total_extracted_size_bytes,
        max_depth_reached=row.max_depth_reached,
        provider_name=row.provider_name,
        model_name=row.model_name,
        analysis=row.analysis,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        total_tokens=row.total_tokens,
        estimated_cost_usd=row.estimated_cost_usd,
        cost_status=row.cost_status,
        cost_currency=row.cost_currency,
        pricing_source=row.pricing_source,
        created_at=row.created_at,
    )
