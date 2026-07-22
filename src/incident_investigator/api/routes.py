import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from openai import AuthenticationError, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession

from incident_investigator.database.connection import get_database_session
from incident_investigator.models.incident import IncidentAnalysis
from incident_investigator.models.incident_record import (
    IncidentCreatedResponse,
    IncidentResponse,
)
from incident_investigator.models.investigation import (
    InvestigationStoredResponse,
    OrchestrationResponse,
)
from incident_investigator.repositories.incident_repository import (
    IncidentRepository,
)
from incident_investigator.repositories.investigation_repository import (
    InvestigationRepository,
)
from incident_investigator.services.investigation_service import investigate_log
from incident_investigator.services.orchestrated_investigation_service import (
    run_and_store_investigation,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/incidents",
    tags=["incidents"],
)

MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024


def build_incident_response(
    *,
    record,
) -> IncidentResponse:
    return IncidentResponse(
        id=record.id,
        status=record.status,
        filename=record.filename,
        created_at=record.created_at,
        analysis=IncidentAnalysis.model_validate(record.analysis),
    )


@router.post(
    "/analyze",
    response_model=IncidentCreatedResponse,
    status_code=201,
)
async def analyze_incident(
    log_file: Annotated[UploadFile, File()],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> IncidentCreatedResponse:
    raw_content = await log_file.read()

    if not raw_content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded log is empty.",
        )

    if len(raw_content) > MAX_LOG_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Log file exceeds the 10 MB limit.",
        )

    filename = log_file.filename or "unknown.log"

    decoded_log = raw_content.decode(
        "utf-8",
        errors="replace",
    )

    try:
        analysis = await investigate_log(decoded_log)

        repository = IncidentRepository(session)

        record = await repository.create(
            filename=filename,
            raw_log=decoded_log,
            analysis=analysis,
        )

        await session.commit()
        await session.refresh(record)

        return IncidentCreatedResponse(
            id=record.id,
            status=record.status,
            filename=record.filename,
            created_at=record.created_at,
            analysis=analysis,
        )

    except AuthenticationError as exc:
        await session.rollback()

        logger.exception(
            "AI provider authentication failed",
        )

        raise HTTPException(
            status_code=503,
            detail="AI provider authentication failed.",
        ) from exc

    except RateLimitError as exc:
        await session.rollback()

        logger.exception(
            "AI provider quota or rate limit exceeded",
        )

        if "insufficient_quota" in str(exc):
            detail = "AI provider quota is unavailable. Check billing and project limits."
        else:
            detail = "AI provider rate limit exceeded."

        raise HTTPException(
            status_code=429,
            detail=detail,
        ) from exc

    except HTTPException:
        await session.rollback()
        raise

    except Exception as exc:
        await session.rollback()

        logger.exception(
            "Incident analysis failed",
        )

        raise HTTPException(
            status_code=500,
            detail=(f"Incident analysis failed: {type(exc).__name__}"),
        ) from exc


@router.post(
    "/{incident_id}/orchestrate",
    response_model=OrchestrationResponse,
    status_code=201,
)
async def orchestrate_existing_incident(
    incident_id: str,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> OrchestrationResponse:
    incident_repository = IncidentRepository(session)

    incident = await incident_repository.get_by_id(
        incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found.",
        )

    if not incident.raw_log.strip():
        raise HTTPException(
            status_code=409,
            detail="Incident does not contain a stored log.",
        )

    try:
        stored_investigation, result = await run_and_store_investigation(
            session=session,
            incident_id=incident.id,
            log_text=incident.raw_log,
        )

        await session.commit()
        await session.refresh(stored_investigation)

        return OrchestrationResponse(
            investigation_id=stored_investigation.id,
            incident_id=incident.id,
            model_name=stored_investigation.model_name,
            created_at=stored_investigation.created_at,
            result=result,
        )

    except AuthenticationError as exc:
        await session.rollback()

        logger.exception(
            "AI provider authentication failed during orchestration",
        )

        raise HTTPException(
            status_code=503,
            detail="AI provider authentication failed.",
        ) from exc

    except RateLimitError as exc:
        await session.rollback()

        logger.exception(
            "AI provider quota or rate limit exceeded during orchestration",
        )

        if "insufficient_quota" in str(exc):
            detail = "AI provider quota is unavailable. Check billing and project limits."
        else:
            detail = "AI provider rate limit exceeded."

        raise HTTPException(
            status_code=429,
            detail=detail,
        ) from exc

    except HTTPException:
        await session.rollback()
        raise

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
) -> list[InvestigationStoredResponse]:
    incident_repository = IncidentRepository(session)

    incident = await incident_repository.get_by_id(
        incident_id,
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
) -> InvestigationStoredResponse:
    repository = InvestigationRepository(session)
    investigation = await repository.get_by_id(investigation_id)

    if investigation is None:
        raise HTTPException(
            status_code=404,
            detail="Investigation not found.",
        )

    return InvestigationStoredResponse.model_validate(investigation)


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
)
async def get_incident(
    incident_id: str,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> IncidentResponse:
    repository = IncidentRepository(session)

    record = await repository.get_by_id(
        incident_id,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found.",
        )

    return build_incident_response(
        record=record,
    )
