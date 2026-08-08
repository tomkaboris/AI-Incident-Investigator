import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from incident_investigator.config import Settings
from incident_investigator.database.connection import create_database_engine
from incident_investigator.database.models import Base


@pytest.mark.asyncio
async def test_sqlite_engine_creates_schema(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        ai_api_key="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
    )
    engine = create_database_engine(settings)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        assert session is not None
    await engine.dispose()
