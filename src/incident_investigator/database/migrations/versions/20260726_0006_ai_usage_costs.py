"""Add AI token usage and estimated cost metadata.

Revision ID: 20260726_0006
Revises: 20260726_0005
"""

import sqlalchemy as sa
from alembic import op

revision = "20260726_0006"
down_revision = "20260726_0005"
branch_labels = None
depends_on = None


def _cost_columns() -> list[sa.Column]:
    return [
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(18, 8), nullable=True),
        sa.Column("cost_status", sa.String(50), nullable=False, server_default="usage_unavailable"),
        sa.Column("cost_currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("pricing_source", sa.String(100), nullable=True),
    ]


def upgrade() -> None:
    with op.batch_alter_table("incidents") as batch_op:
        batch_op.add_column(sa.Column("initial_provider_name", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("initial_model_name", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("initial_input_tokens", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("initial_output_tokens", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("initial_total_tokens", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("initial_estimated_cost_usd", sa.Numeric(18, 8), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "initial_cost_status",
                sa.String(50),
                nullable=False,
                server_default="usage_unavailable",
            )
        )
        batch_op.add_column(
            sa.Column("initial_cost_currency", sa.String(10), nullable=False, server_default="USD")
        )
        batch_op.add_column(sa.Column("initial_pricing_source", sa.String(100), nullable=True))

    with op.batch_alter_table("incident_investigations") as batch_op:
        batch_op.add_column(sa.Column("total_tokens", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("estimated_cost_usd", sa.Numeric(18, 8), nullable=True))
        batch_op.add_column(
            sa.Column(
                "cost_status", sa.String(50), nullable=False, server_default="usage_unavailable"
            )
        )
        batch_op.add_column(
            sa.Column("cost_currency", sa.String(10), nullable=False, server_default="USD")
        )
        batch_op.add_column(sa.Column("pricing_source", sa.String(100), nullable=True))

    with op.batch_alter_table("incident_archives") as batch_op:
        for column in _cost_columns():
            batch_op.add_column(column)


def downgrade() -> None:
    with op.batch_alter_table("incident_archives") as batch_op:
        for name in (
            "pricing_source",
            "cost_currency",
            "cost_status",
            "estimated_cost_usd",
            "total_tokens",
            "output_tokens",
            "input_tokens",
        ):
            batch_op.drop_column(name)
    with op.batch_alter_table("incident_investigations") as batch_op:
        for name in (
            "pricing_source",
            "cost_currency",
            "cost_status",
            "estimated_cost_usd",
            "total_tokens",
        ):
            batch_op.drop_column(name)
    with op.batch_alter_table("incidents") as batch_op:
        for name in (
            "initial_pricing_source",
            "initial_cost_currency",
            "initial_cost_status",
            "initial_estimated_cost_usd",
            "initial_total_tokens",
            "initial_output_tokens",
            "initial_input_tokens",
            "initial_model_name",
            "initial_provider_name",
        ):
            batch_op.drop_column(name)
