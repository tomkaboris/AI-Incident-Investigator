"""Add recursive archive investigation tables.
Revision ID: 20260726_0005
Revises: 20260726_0004
"""

import sqlalchemy as sa
from alembic import op

revision = "20260726_0005"
down_revision = "20260726_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "incident_archives",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "incident_id",
            sa.String(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("uploaded_filename", sa.String(255), nullable=False),
        sa.Column("storage_backend", sa.String(50), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("problem_description", sa.Text(), nullable=False),
        sa.Column("incident_time", sa.DateTime(timezone=True)),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("system_name", sa.String(255)),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("artifact_count", sa.Integer(), nullable=False),
        sa.Column("total_extracted_size_bytes", sa.Integer(), nullable=False),
        sa.Column("max_depth_reached", sa.Integer(), nullable=False),
        sa.Column("analysis", sa.JSON(), nullable=False),
        sa.Column("provider_name", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incident_archives_incident_id", "incident_archives", ["incident_id"])
    op.create_index("ix_incident_archives_status", "incident_archives", ["status"])
    op.create_index(
        "ix_incident_archives_checksum_sha256", "incident_archives", ["checksum_sha256"]
    )
    op.create_table(
        "incident_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "archive_id",
            sa.Integer(),
            sa.ForeignKey("incident_archives.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "incident_id",
            sa.String(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_path", sa.String(2048), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("storage_backend", sa.String(50), nullable=False),
        sa.Column("source_archive_path", sa.String(2048)),
        sa.Column("archive_depth", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("extension", sa.String(50)),
        sa.Column("content_type", sa.String(255)),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("component", sa.String(100)),
        sa.Column("log_format", sa.String(100)),
        sa.Column("encoding", sa.String(50)),
        sa.Column("earliest_timestamp", sa.DateTime(timezone=True)),
        sa.Column("latest_timestamp", sa.DateTime(timezone=True)),
        sa.Column("is_archive", sa.Boolean(), nullable=False),
        sa.Column("is_log_candidate", sa.Boolean(), nullable=False),
        sa.Column("processing_status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ("archive_id", "incident_id", "checksum_sha256", "component", "is_log_candidate"):
        op.create_index(f"ix_incident_artifacts_{col}", "incident_artifacts", [col])
    op.create_table(
        "incident_log_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "incident_id",
            sa.String(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "artifact_id",
            sa.Integer(),
            sa.ForeignKey("incident_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("component", sa.String(100), nullable=False),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True)),
        sa.Column("original_timestamp", sa.String(100)),
        sa.Column("severity", sa.String(50)),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("line_number", sa.Integer()),
        sa.Column("correlation_ids", sa.JSON(), nullable=False),
    )
    for col in ("incident_id", "artifact_id", "component", "timestamp_utc", "severity"):
        op.create_index(f"ix_incident_log_events_{col}", "incident_log_events", [col])


def downgrade():
    op.drop_table("incident_log_events")
    op.drop_table("incident_artifacts")
    op.drop_table("incident_archives")
