"""Move raw log content out of the relational database.

Revision ID: 20260725_0002
Revises: 20260725_0001

Existing raw_log values are intentionally not copied to object storage by this
schema migration. Export important legacy logs before upgrading, then re-import
them through the API or a dedicated deployment migration.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260725_0002"
down_revision = "20260725_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("incidents") as batch_op:
        batch_op.add_column(sa.Column("log_storage_backend", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("log_storage_key", sa.String(1024), nullable=True))
        batch_op.add_column(sa.Column("log_checksum_sha256", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("log_size_bytes", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("log_content_type", sa.String(255), nullable=True))

    connection = op.get_bind()
    incident_count = connection.execute(sa.text("SELECT COUNT(*) FROM incidents")).scalar_one()
    if incident_count:
        raise RuntimeError(
            "Version 0.5.0 cannot automatically externalize existing raw_log values. "
            "Export or recreate existing incidents before running this migration."
        )

    with op.batch_alter_table("incidents") as batch_op:
        batch_op.alter_column("log_storage_backend", nullable=False)
        batch_op.alter_column("log_storage_key", nullable=False)
        batch_op.alter_column("log_checksum_sha256", nullable=False)
        batch_op.alter_column("log_size_bytes", nullable=False)
        batch_op.alter_column("log_content_type", nullable=False)
        batch_op.create_unique_constraint("uq_incidents_log_storage_key", ["log_storage_key"])
        batch_op.create_index("ix_incidents_log_checksum_sha256", ["log_checksum_sha256"])
        batch_op.drop_column("raw_log")


def downgrade() -> None:
    with op.batch_alter_table("incidents") as batch_op:
        batch_op.add_column(sa.Column("raw_log", sa.Text(), nullable=True))
        batch_op.drop_index("ix_incidents_log_checksum_sha256")
        batch_op.drop_constraint("uq_incidents_log_storage_key", type_="unique")
        batch_op.drop_column("log_content_type")
        batch_op.drop_column("log_size_bytes")
        batch_op.drop_column("log_checksum_sha256")
        batch_op.drop_column("log_storage_key")
        batch_op.drop_column("log_storage_backend")
