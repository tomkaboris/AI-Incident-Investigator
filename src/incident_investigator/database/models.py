from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class MemberRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    INVESTIGATOR = "investigator"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    memberships: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    members: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_member"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default=MemberRole.INVESTIGATOR.value
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    organization: Mapped[Organization] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class IncidentRecord(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    assigned_to_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    problem_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    log_storage_backend: Mapped[str] = mapped_column(String(50), nullable=False)
    log_storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    log_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    log_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    log_content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="analyzed")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    probable_root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    analysis: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    initial_provider_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    initial_model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    initial_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    initial_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    initial_total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    initial_estimated_cost_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 8), nullable=True
    )
    initial_cost_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="usage_unavailable"
    )
    initial_cost_currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    initial_pricing_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    investigations: Mapped[list["IncidentInvestigation"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", passive_deletes=True
    )
    archives: Mapped[list["IncidentArchive"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", passive_deletes=True
    )
    activities: Mapped[list["IncidentActivity"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", passive_deletes=True
    )
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_user_id])
    assigned_to: Mapped[User | None] = relationship(foreign_keys=[assigned_to_user_id])


class IncidentInvestigation(Base):
    __tablename__ = "incident_investigations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    classification_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    root_cause_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, default="openai")
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1")
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    cost_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="usage_unavailable"
    )
    cost_currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    pricing_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    classification: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    root_cause: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    fix_recommendation: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    report: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    full_result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    incident: Mapped[IncidentRecord] = relationship(back_populates="investigations")
    created_by: Mapped[User] = relationship()


class IncidentActivity(Base):
    __tablename__ = "incident_activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    incident: Mapped[IncidentRecord] = relationship(back_populates="activities")
    user: Mapped[User | None] = relationship()


class IncidentArchive(Base):
    __tablename__ = "incident_archives"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    incident_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="UTC")
    system_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed", index=True)
    artifact_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_extracted_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_depth_reached: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    cost_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="usage_unavailable"
    )
    cost_currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    pricing_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    incident: Mapped[IncidentRecord] = relationship(back_populates="archives")
    artifacts: Mapped[list["IncidentArtifact"]] = relationship(
        back_populates="archive", cascade="all, delete-orphan", passive_deletes=True
    )


class IncidentArtifact(Base):
    __tablename__ = "incident_artifacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    archive_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("incident_archives.id", ondelete="CASCADE"), nullable=False, index=True
    )
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    storage_backend: Mapped[str] = mapped_column(String(50), nullable=False)
    source_archive_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    archive_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    component: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    log_format: Mapped[str | None] = mapped_column(String(100), nullable=True)
    encoding: Mapped[str | None] = mapped_column(String(50), nullable=True)
    earliest_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    latest_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_archive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_log_candidate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    processing_status: Mapped[str] = mapped_column(String(50), nullable=False, default="indexed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    archive: Mapped[IncidentArchive] = relationship(back_populates="artifacts")


class IncidentLogEvent(Base):
    __tablename__ = "incident_log_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("incident_artifacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timestamp_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    original_timestamp: Mapped[str | None] = mapped_column(String(100), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correlation_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
