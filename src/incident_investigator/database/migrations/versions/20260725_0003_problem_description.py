"""Add optional user-reported problem description.

Revision ID: 20260725_0003
Revises: 20260725_0002
"""

import sqlalchemy as sa
from alembic import op

revision = "20260725_0003"
down_revision = "20260725_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column("problem_description", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("incidents", "problem_description")
