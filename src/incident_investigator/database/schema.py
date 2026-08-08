from sqlalchemy.ext.asyncio import AsyncEngine

from incident_investigator.database.models import Base


async def initialize_database(engine: AsyncEngine) -> None:
    """Create database tables for local development.

    Production deployments should set DATABASE_AUTO_CREATE=false and run
    ``incident-investigator migrate`` explicitly.
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
