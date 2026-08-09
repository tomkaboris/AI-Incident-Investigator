from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from incident_investigator import __version__
from incident_investigator.ai import create_ai_runtime
from incident_investigator.api.archive_routes import router as archive_router
from incident_investigator.api.auth_routes import router as auth_router
from incident_investigator.api.collaboration_routes import router as collaboration_router
from incident_investigator.api.dashboard_routes import router as dashboard_api_router
from incident_investigator.api.routes import router
from incident_investigator.auth.middleware import CSRFMiddleware
from incident_investigator.config import get_settings
from incident_investigator.database.connection import engine
from incident_investigator.database.schema import initialize_database
from incident_investigator.storage import get_log_storage


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    create_ai_runtime(settings)
    get_log_storage()

    if settings.database_auto_create:
        await initialize_database(engine)

    yield
    await engine.dispose()


app = FastAPI(
    title="AI Incident Investigator",
    description="Provider-neutral AI-assisted incident investigation and root-cause analysis.",
    version=__version__,
    lifespan=lifespan,
)
settings = get_settings()
app.add_middleware(CSRFMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    session_cookie=settings.session_cookie_name,
    max_age=settings.session_max_age_seconds,
    same_site="lax",
    https_only=settings.session_https_only,
)
app.include_router(auth_router)
app.include_router(archive_router)
app.include_router(router)
app.include_router(collaboration_router)
app.include_router(dashboard_api_router)

DASHBOARD_DIR = Path(__file__).resolve().parent / "dashboard" / "static"
app.mount("/dashboard/assets", StaticFiles(directory=DASHBOARD_DIR), name="dashboard-assets")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")


@app.get("/login", include_in_schema=False)
async def login_page() -> FileResponse:
    return FileResponse(DASHBOARD_DIR / "auth.html")


@app.get("/register", include_in_schema=False)
async def register_page() -> FileResponse:
    return FileResponse(DASHBOARD_DIR / "auth.html")


@app.get("/dashboard", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(DASHBOARD_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "healthy",
        "ai_provider": settings.ai_provider.value,
        "ai_model": settings.ai_model,
        "ai_pricing_configured": str(
            settings.get_model_pricing(settings.ai_provider.value, settings.ai_model) is not None
        ).lower(),
        "database": settings.database_url.split(":", maxsplit=1)[0],
        "storage_backend": settings.storage_backend.value,
        "github_source_lookup": (
            "enabled"
            if settings.github_enabled and settings.github_source_lookup_enabled
            else "disabled"
        ),
    }
