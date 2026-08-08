from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from incident_investigator.database.models import IncidentRecord
from incident_investigator.models.incident import IncidentAnalysis


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        filename: str,
        incident_id: str,
        organization_id: str,
        created_by_user_id: str,
        problem_description: str | None,
        storage_backend: str,
        storage_key: str,
        checksum_sha256: str,
        size_bytes: int,
        content_type: str,
        analysis: IncidentAnalysis,
        initial_provider_name: str | None = None,
        initial_model_name: str | None = None,
        initial_input_tokens: int | None = None,
        initial_output_tokens: int | None = None,
        initial_total_tokens: int | None = None,
        initial_estimated_cost_usd=None,
        initial_cost_status: str = "usage_unavailable",
        initial_cost_currency: str = "USD",
        initial_pricing_source: str | None = None,
    ) -> IncidentRecord:
        record = IncidentRecord(
            id=incident_id,
            organization_id=organization_id,
            created_by_user_id=created_by_user_id,
            filename=filename,
            problem_description=problem_description,
            log_storage_backend=storage_backend,
            log_storage_key=storage_key,
            log_checksum_sha256=checksum_sha256,
            log_size_bytes=size_bytes,
            log_content_type=content_type,
            title=analysis.title,
            category=str(analysis.category),
            severity=str(analysis.severity),
            summary=analysis.summary,
            probable_root_cause=analysis.probable_root_cause,
            confidence=analysis.confidence,
            analysis=analysis.model_dump(mode="json"),
            initial_provider_name=initial_provider_name,
            initial_model_name=initial_model_name,
            initial_input_tokens=initial_input_tokens,
            initial_output_tokens=initial_output_tokens,
            initial_total_tokens=initial_total_tokens,
            initial_estimated_cost_usd=initial_estimated_cost_usd,
            initial_cost_status=initial_cost_status,
            initial_cost_currency=initial_cost_currency,
            initial_pricing_source=initial_pricing_source,
        )

        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)

        return record

    async def get_by_id(
        self,
        incident_id: str,
        organization_id: str,
    ) -> IncidentRecord | None:
        statement = (
            select(IncidentRecord)
            .options(
                selectinload(IncidentRecord.created_by),
                selectinload(IncidentRecord.assigned_to),
            )
            .where(
                IncidentRecord.id == incident_id,
                IncidentRecord.organization_id == organization_id,
            )
        )

        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
