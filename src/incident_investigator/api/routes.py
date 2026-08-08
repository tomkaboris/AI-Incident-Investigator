import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from incident_investigator.ai.exceptions import (
    AIAuthenticationError,
    AIProviderError,
    AIQuotaError,
    AIRateLimitError,
)
from incident_investigator.auth.context import CurrentAuth, get_auth_context
from incident_investigator.config import get_settings
from incident_investigator.database.connection import get_database_session
from incident_investigator.database.models import MemberRole
from incident_investigator.models.incident import IncidentAnalysis
from incident_investigator.models.incident_record import (
    IncidentCreatedResponse,
    IncidentResponse,
)
from incident_investigator.models.investigation import (
    InvestigationStoredResponse,
    OrchestrationResponse,
)
from incident_investigator.repositories.activity_repository import ActivityRepository
from incident_investigator.repositories.incident_repository import (
    IncidentRepository,
)
from incident_investigator.repositories.investigation_repository import (
    InvestigationRepository,
)
from incident_investigator.security import UploadValidationError, validate_log_upload
from incident_investigator.services.investigation_service import investigate_log_with_usage
from incident_investigator.services.orchestrated_investigation_service import (
    run_and_store_investigation,
)
from incident_investigator.services.problem_context import normalize_problem_description
from incident_investigator.storage import (
    build_storage_key,
    calculate_sha256,
    get_log_storage,
    read_verified_log,
)
from incident_investigator.storage.exceptions import (
    LogIntegrityError,
    LogNotFoundError,
    LogStorageError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/incidents",
    tags=["incidents"],
    dependencies=[Depends(get_auth_context)],
)


def build_incident_response(
    *,
    record,
) -> IncidentResponse:
    return IncidentResponse(
        id=record.id,
        status=record.status,
        organization_id=record.organization_id,
        created_by_user_id=record.created_by_user_id,
        created_by_name=getattr(record.created_by, "full_name", None),
        assigned_to_user_id=record.assigned_to_user_id,
        assigned_to_name=getattr(record.assigned_to, "full_name", None),
        filename=record.filename,
        problem_description=record.problem_description,
        created_at=record.created_at,
        log_storage_backend=record.log_storage_backend,
        log_checksum_sha256=record.log_checksum_sha256,
        log_size_bytes=record.log_size_bytes,
        log_content_type=record.log_content_type,
        analysis=IncidentAnalysis.model_validate(record.analysis),
        initial_provider_name=record.initial_provider_name,
        initial_model_name=record.initial_model_name,
        initial_input_tokens=record.initial_input_tokens,
        initial_output_tokens=record.initial_output_tokens,
        initial_total_tokens=record.initial_total_tokens,
        initial_estimated_cost_usd=record.initial_estimated_cost_usd,
        initial_cost_status=record.initial_cost_status,
        initial_cost_currency=record.initial_cost_currency,
        initial_pricing_source=record.initial_pricing_source,
    )


@router.post(
    "/analyze",
    response_model=IncidentCreatedResponse,
    status_code=201,
)
async def analyze_incident(
    log_file: Annotated[UploadFile, File()],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
    problem_description: Annotated[
        str | None,
        Form(
            description=(
                "Optional description of observed symptoms, affected environment, "
                "timing, reproduction steps, and recent changes."
            ),
        ),
    ] = None,
) -> IncidentCreatedResponse:
    if auth.membership.role == MemberRole.VIEWER.value:
        raise HTTPException(status_code=403, detail="Viewer cannot create incidents.")
    settings = get_settings()
    raw_content = await log_file.read()

    try:
        upload = validate_log_upload(
            filename=log_file.filename,
            content=raw_content,
            content_type=log_file.content_type,
            max_size_bytes=settings.max_upload_size_bytes,
            allowed_extensions=settings.allowed_log_extension_set,
            allowed_content_types=settings.allowed_log_content_type_set,
            reject_binary_files=settings.reject_binary_logs,
        )
    except UploadValidationError as exc:
        status_code = 413 if "upload limit" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    decoded_log = upload.content.decode("utf-8", errors="replace")
    normalized_problem_description = normalize_problem_description(
        problem_description,
        max_characters=settings.max_problem_description_characters,
    )
    storage = get_log_storage()
    incident_id = str(uuid4())
    storage_key = build_storage_key(incident_id=incident_id, filename=upload.filename)
    checksum = calculate_sha256(upload.content)
    stored = False
    committed = False

    try:
        analysis, usage = await investigate_log_with_usage(
            decoded_log,
            problem_description=normalized_problem_description,
        )
        await storage.save(
            key=storage_key,
            content=upload.content,
            content_type=upload.content_type,
        )
        stored = True

        repository = IncidentRepository(session)
        record = await repository.create(
            incident_id=incident_id,
            organization_id=auth.organization.id,
            created_by_user_id=auth.user.id,
            filename=upload.filename,
            problem_description=normalized_problem_description,
            storage_backend=storage.backend_name,
            storage_key=storage_key,
            checksum_sha256=checksum,
            size_bytes=len(upload.content),
            content_type=upload.content_type,
            analysis=analysis,
            initial_provider_name=settings.ai_provider.value,
            initial_model_name=settings.ai_model,
            initial_input_tokens=usage.input_tokens,
            initial_output_tokens=usage.output_tokens,
            initial_total_tokens=usage.total_tokens,
            initial_estimated_cost_usd=usage.estimated_cost_usd,
            initial_cost_status=usage.cost_status,
            initial_cost_currency=usage.currency,
            initial_pricing_source=usage.pricing_source,
        )

        await ActivityRepository(session).add(
            incident_id=record.id,
            user_id=auth.user.id,
            action="incident_created",
            details={"filename": record.filename},
        )
        await session.commit()
        await session.refresh(record)
        committed = True

        return IncidentCreatedResponse(
            id=record.id,
            status=record.status,
            organization_id=record.organization_id,
            created_by_user_id=record.created_by_user_id,
            created_by_name=auth.user.full_name,
            assigned_to_user_id=record.assigned_to_user_id,
            assigned_to_name=None,
            filename=record.filename,
            problem_description=record.problem_description,
            created_at=record.created_at,
            log_storage_backend=record.log_storage_backend,
            log_checksum_sha256=record.log_checksum_sha256,
            log_size_bytes=record.log_size_bytes,
            log_content_type=record.log_content_type,
            analysis=analysis,
            initial_provider_name=record.initial_provider_name,
            initial_model_name=record.initial_model_name,
            initial_input_tokens=record.initial_input_tokens,
            initial_output_tokens=record.initial_output_tokens,
            initial_total_tokens=record.initial_total_tokens,
            initial_estimated_cost_usd=record.initial_estimated_cost_usd,
            initial_cost_status=record.initial_cost_status,
            initial_cost_currency=record.initial_cost_currency,
            initial_pricing_source=record.initial_pricing_source,
        )

    except AIAuthenticationError as exc:
        await session.rollback()
        logger.exception("AI provider authentication failed")
        raise HTTPException(status_code=503, detail="AI provider authentication failed.") from exc
    except AIQuotaError as exc:
        await session.rollback()
        logger.exception("AI provider quota is unavailable")
        raise HTTPException(
            status_code=429,
            detail="AI provider quota is unavailable. Check billing and project limits.",
        ) from exc
    except AIRateLimitError as exc:
        await session.rollback()
        logger.exception("AI provider quota or rate limit exceeded")
        raise HTTPException(status_code=429, detail="AI provider rate limit exceeded.") from exc
    except AIProviderError as exc:
        await session.rollback()
        logger.exception("AI provider request failed")
        raise HTTPException(status_code=502, detail="AI provider request failed.") from exc
    except LogStorageError as exc:
        await session.rollback()
        logger.exception("Log storage request failed")
        raise HTTPException(status_code=503, detail="Log storage is unavailable.") from exc
    except HTTPException:
        await session.rollback()
        raise
    except Exception as exc:
        await session.rollback()
        logger.exception("Incident analysis failed")
        raise HTTPException(
            status_code=500,
            detail=f"Incident analysis failed: {type(exc).__name__}",
        ) from exc
    finally:
        if stored and not committed:
            try:
                await storage.delete(key=storage_key)
            except LogStorageError:
                logger.exception("Failed to clean up an orphaned stored log")


@router.post(
    "/{incident_id}/orchestrate",
    response_model=OrchestrationResponse,
    status_code=201,
)
async def orchestrate_existing_incident(
    incident_id: str,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
) -> OrchestrationResponse:
    if auth.membership.role == MemberRole.VIEWER.value:
        raise HTTPException(status_code=403, detail="Viewer cannot run investigations.")
    incident_repository = IncidentRepository(session)

    incident = await incident_repository.get_by_id(
        incident_id,
        auth.organization.id,
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found.",
        )

    try:
        raw_content = await read_verified_log(incident, get_log_storage())
        log_text = raw_content.decode("utf-8", errors="replace")
        stored_investigation, result = await run_and_store_investigation(
            session=session,
            incident_id=incident.id,
            created_by_user_id=auth.user.id,
            log_text=log_text,
            problem_description=incident.problem_description,
        )

        await ActivityRepository(session).add(
            incident_id=incident.id,
            user_id=auth.user.id,
            action="multi_agent_investigation_completed",
            details={"investigation_id": stored_investigation.id},
        )
        await session.commit()
        await session.refresh(stored_investigation)

        return OrchestrationResponse(
            investigation_id=stored_investigation.id,
            incident_id=incident.id,
            created_by_user_id=auth.user.id,
            provider_name=stored_investigation.provider_name,
            model_name=stored_investigation.model_name,
            input_tokens=stored_investigation.input_tokens,
            output_tokens=stored_investigation.output_tokens,
            total_tokens=stored_investigation.total_tokens,
            estimated_cost_usd=stored_investigation.estimated_cost_usd,
            cost_status=stored_investigation.cost_status,
            cost_currency=stored_investigation.cost_currency,
            pricing_source=stored_investigation.pricing_source,
            created_at=stored_investigation.created_at,
            result=result,
        )

    except AIAuthenticationError as exc:
        await session.rollback()

        logger.exception(
            "AI provider authentication failed during orchestration",
        )

        raise HTTPException(
            status_code=503,
            detail="AI provider authentication failed.",
        ) from exc

    except AIQuotaError as exc:
        await session.rollback()
        logger.exception("AI provider quota is unavailable")
        raise HTTPException(
            status_code=429,
            detail="AI provider quota is unavailable. Check billing and project limits.",
        ) from exc

    except AIRateLimitError as exc:
        await session.rollback()

        logger.exception(
            "AI provider quota or rate limit exceeded during orchestration",
        )

        raise HTTPException(
            status_code=429,
            detail="AI provider rate limit exceeded.",
        ) from exc

    except HTTPException:
        await session.rollback()
        raise

    except LogNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Stored log content is missing.") from exc
    except LogIntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Stored log failed checksum verification.",
        ) from exc
    except LogStorageError as exc:
        await session.rollback()
        raise HTTPException(status_code=503, detail="Log storage is unavailable.") from exc

    except AIProviderError as exc:
        await session.rollback()
        logger.exception("AI provider request failed")
        raise HTTPException(status_code=502, detail="AI provider request failed.") from exc

    except Exception as exc:
        await session.rollback()

        logger.exception(
            "Incident orchestration failed",
        )

        raise HTTPException(
            status_code=500,
            detail=(f"Incident orchestration failed: {type(exc).__name__}"),
        ) from exc


@router.get(
    "/{incident_id}/investigations",
    response_model=list[InvestigationStoredResponse],
)
async def list_incident_investigations(
    incident_id: str,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
) -> list[InvestigationStoredResponse]:
    incident_repository = IncidentRepository(session)

    incident = await incident_repository.get_by_id(
        incident_id,
        auth.organization.id,
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found.",
        )

    investigation_repository = InvestigationRepository(
        session,
    )

    investigations = await investigation_repository.list_by_incident_id(
        incident_id,
        auth.organization.id,
    )

    return [
        InvestigationStoredResponse.model_validate(
            investigation,
        )
        for investigation in investigations
    ]


@router.get(
    "/investigations/{investigation_id}",
    response_model=InvestigationStoredResponse,
)
async def get_investigation(
    investigation_id: int,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
) -> InvestigationStoredResponse:
    repository = InvestigationRepository(session)
    investigation = await repository.get_by_id(investigation_id, auth.organization.id)

    if investigation is None:
        raise HTTPException(
            status_code=404,
            detail="Investigation not found.",
        )

    return InvestigationStoredResponse.model_validate(investigation)


@router.get("/{incident_id}/log")
async def download_incident_log(
    incident_id: str,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
) -> Response:
    repository = IncidentRepository(session)
    record = await repository.get_by_id(incident_id, auth.organization.id)
    if record is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    try:
        content = await read_verified_log(record, get_log_storage())
    except LogNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Stored log content was not found.") from exc
    except LogIntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Stored log failed checksum verification.",
        ) from exc
    except LogStorageError as exc:
        raise HTTPException(status_code=503, detail="Log storage is unavailable.") from exc
    return Response(
        content=content,
        media_type=record.log_content_type,
        headers={"Content-Disposition": f'attachment; filename="{record.filename}"'},
    )


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
)
async def get_incident(
    incident_id: str,
    session: Annotated[AsyncSession, Depends(get_database_session)],
    auth: CurrentAuth,
) -> IncidentResponse:
    repository = IncidentRepository(session)

    record = await repository.get_by_id(
        incident_id,
        auth.organization.id,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found.",
        )

    return build_incident_response(
        record=record,
    )
