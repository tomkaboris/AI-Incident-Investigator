"""Add multi-user workspaces and audit trail.
Revision ID: 20260726_0004
Revises: 20260725_0003
"""

import sqlalchemy as sa
from alembic import op

revision = "20260726_0004"
down_revision = "20260725_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "organization_members",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
    )
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT COUNT(*) FROM incidents")).scalar_one():
        raise RuntimeError(
            "Export or recreate existing incidents before enabling multi-user workspaces."
        )
    with op.batch_alter_table("incidents") as b:
        b.add_column(sa.Column("organization_id", sa.String(36), nullable=True))
        b.add_column(sa.Column("created_by_user_id", sa.String(36), nullable=True))
        b.add_column(sa.Column("assigned_to_user_id", sa.String(36), nullable=True))
        b.create_foreign_key(
            "fk_incident_org", "organizations", ["organization_id"], ["id"], ondelete="CASCADE"
        )
        b.create_foreign_key("fk_incident_creator", "users", ["created_by_user_id"], ["id"])
        b.create_foreign_key("fk_incident_assignee", "users", ["assigned_to_user_id"], ["id"])
    with op.batch_alter_table("incident_investigations") as b:
        b.add_column(sa.Column("created_by_user_id", sa.String(36), nullable=True))
        b.create_foreign_key("fk_investigation_creator", "users", ["created_by_user_id"], ["id"])
        b.alter_column("created_by_user_id", nullable=False)
    op.create_table(
        "incident_activities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "incident_id",
            sa.String(36),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("incident_activities")
    with op.batch_alter_table("incident_investigations") as b:
        b.drop_column("created_by_user_id")
    with op.batch_alter_table("incidents") as b:
        b.drop_column("assigned_to_user_id")
        b.drop_column("created_by_user_id")
        b.drop_column("organization_id")
    op.drop_table("organization_members")
    op.drop_table("organizations")
    op.drop_table("users")
