from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from agents import set_default_openai_key
from fastapi import FastAPI

from incident_investigator.api.routes import router
from incident_investigator.config import get_settings
from incident_investigator.database.connection import engine
from incident_investigator.database.schema import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    set_default_openai_key(settings.openai_api_key)

    await initialize_database(engine)

    yield

    await engine.dispose()


app = FastAPI(
    title="AI Incident Investigator",
    description="AI-assisted incident investigation and root-cause analysis.",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
