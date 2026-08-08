"""Initial multi-provider schema.

Revision ID: 20260725_0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "20260725_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("raw_log", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("probable_root_cause", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("analysis", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "incident_investigations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "incident_id",
            sa.String(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("classification_confidence", sa.Float(), nullable=False),
        sa.Column("root_cause_confidence", sa.Float(), nullable=False),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False),
        sa.Column("provider_name", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("classification", sa.JSON(), nullable=False),
        sa.Column("root_cause", sa.JSON(), nullable=False),
        sa.Column("fix_recommendation", sa.JSON(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("full_result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_incident_investigations_incident_id",
        "incident_investigations",
        ["incident_id"],
    )

    op.create_index(
        "ix_incident_investigations_category",
        "incident_investigations",
        ["category"],
    )

    op.create_index(
        "ix_incident_investigations_requires_human_review",
        "incident_investigations",
        ["requires_human_review"],
    )


def downgrade() -> None:
    op.drop_table("incident_investigations")
    op.drop_table("incidents")
