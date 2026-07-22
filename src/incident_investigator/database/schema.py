from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

from incident_investigator.database.models import Base


async def initialize_database(engine: AsyncEngine) -> None:
    """Create tables and apply minimal SQLite development compatibility updates.

    Alembic should replace this compatibility step before production deployment.
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

        if connection.dialect.name != "sqlite":
            return

        columns = await connection.run_sync(
            lambda sync_connection: {
                column["name"] for column in inspect(sync_connection).get_columns("incidents")
            }
        )

        if "raw_log" not in columns:
            await connection.execute(
                text("ALTER TABLE incidents ADD COLUMN raw_log TEXT NOT NULL DEFAULT ''")
            )
