"""Friendly startup diagnostics for CLI users.

The checks in this module deliberately avoid changing the configuration model
itself. That keeps programmatic, Docker, and CI usage backward compatible while
giving `incident-investigator` users actionable errors before optional imports fail.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

from incident_investigator.config import AIProvider, Settings, StorageBackend


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A single configuration diagnostic shown to CLI users."""

    level: str
    message: str
    hint: str | None = None


_DATABASE_DRIVERS = {
    "sqlite": {
        "module": "aiosqlite",
        "extra": "sqlite",
        "name": "SQLite",
    },
    "postgresql": {
        "module": "asyncpg",
        "extra": "postgresql",
        "name": "PostgreSQL",
    },
    "postgres": {
        "module": "asyncpg",
        "extra": "postgresql",
        "name": "PostgreSQL",
    },
    "mysql": {
        "module": "aiomysql",
        "extra": "mysql",
        "name": "MySQL",
    },
    "mariadb": {
        "module": "aiomysql",
        "extra": "mysql",
        "name": "MySQL/MariaDB",
    },
}


def _module_available(module_name: str) -> bool:
    """Return True when an importable module is installed."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError):
        return False


def _database_backend(database_url: str) -> str:
    """Return the normalized database backend from a SQLAlchemy URL."""
    scheme = database_url.split(":", 1)[0].lower()

    if scheme.startswith("sqlite"):
        return "sqlite"

    if scheme.startswith("postgresql"):
        return "postgresql"

    if scheme.startswith("postgres"):
        return "postgres"

    if scheme.startswith("mysql"):
        return "mysql"

    if scheme.startswith("mariadb"):
        return "mariadb"

    return scheme


def _database_choices_hint() -> str:
    """Return install instructions for every supported database backend."""
    return (
        "SQLite is used by default when DATABASE_URL is not configured.\n\n"
        "Choose the database backend you want to use:\n\n"
        "  SQLite:\n"
        '    pip install "ai-incident-investigator[sqlite]"\n\n'
        "  PostgreSQL:\n"
        '    pip install "ai-incident-investigator[postgresql]"\n\n'
        "  MySQL:\n"
        '    pip install "ai-incident-investigator[mysql]"'
    )


def _database_install_command(extra: str, *, include_s3: bool = False) -> str:
    """Build the appropriate pip install command for a database extra."""
    extras = f"{extra},s3" if include_s3 else extra
    return f'pip install "ai-incident-investigator[{extras}]"'


def collect_diagnostics(
    settings: Settings,
    *,
    cwd: Path | None = None,
) -> list[Diagnostic]:
    """Return actionable configuration and optional-dependency diagnostics."""
    working_directory = cwd or Path.cwd()
    diagnostics: list[Diagnostic] = []

    env_path = working_directory / ".env"

    if not env_path.is_file():
        diagnostics.append(
            Diagnostic(
                level="warning",
                message=f"No .env file found in {working_directory}.",
                hint=(
                    "Create .env in this directory, or provide the same settings "
                    "through environment variables. Environment variables are "
                    "recommended for Docker and CI environments."
                ),
            )
        )

    database_url = str(settings.database_url)
    backend = _database_backend(database_url)
    driver_info = _DATABASE_DRIVERS.get(backend)

    database_explicitly_configured = "database_url" in settings.model_fields_set

    if driver_info:
        module_name = driver_info["module"]
        extra = driver_info["extra"]

        if not _module_available(module_name):
            if database_explicitly_configured:
                diagnostics.append(
                    Diagnostic(
                        level="error",
                        message=(
                            f"Database backend '{backend}' is configured, but the required "
                            f"Python driver '{module_name}' is not installed."
                        ),
                        hint=(
                            "Install the matching database extra:\n\n"
                            f"  {_database_install_command(extra)}"
                        ),
                    )
                )
            else:
                diagnostics.append(
                    Diagnostic(
                        level="error",
                        message=(
                            "No database backend was explicitly configured, "
                            "and no database driver is installed."
                        ),
                        hint=_database_choices_hint(),
                    )
                )
    else:
        diagnostics.append(
            Diagnostic(
                level="error",
                message=(
                    f"Unsupported database backend '{backend}' detected in "
                    "DATABASE_URL."
                ),
                hint=(
                    "Supported database backends are SQLite, PostgreSQL, and MySQL."
                ),
            )
        )

    if settings.storage_backend is StorageBackend.S3 and not _module_available("boto3"):
        if driver_info:
            database_extra = driver_info["extra"]
            install_command = _database_install_command(
                database_extra,
                include_s3=True,
            )

            hint = (
                "Install S3 support together with your configured database "
                f"backend:\n\n  {install_command}"
            )
        else:
            hint = (
                "Install S3 support with:\n\n"
                '  pip install "ai-incident-investigator[s3]"'
            )

        diagnostics.append(
            Diagnostic(
                level="error",
                message=(
                    "S3 storage is configured, but the optional dependency "
                    "'boto3' is not installed."
                ),
                hint=hint,
            )
        )

    if settings.github_enabled:
        if not settings.github_token:
            diagnostics.append(
                Diagnostic(
                    level="error",
                    message=(
                        "GitHub source lookup is enabled, but GITHUB_TOKEN is missing."
                    ),
                    hint=(
                        "Configure a read-only GitHub/GHE token with repository contents "
                        "and code-search access, or set GITHUB_ENABLED=false."
                    ),
                )
            )
        if not settings.github_base_url:
            diagnostics.append(
                Diagnostic(
                    level="warning",
                    message=(
                        "GITHUB_BASE_URL is not configured; https://github.com will be used."
                    ),
                    hint=(
                        "For GitHub Enterprise Server set, for example, "
                        "GITHUB_BASE_URL=https://github.company.example."
                    ),
                )
            )

    if settings.ai_provider is AIProvider.OPENAI and not settings.ai_api_key:
        diagnostics.append(
            Diagnostic(
                level="error",
                message=(
                    "AI_PROVIDER=openai is configured, but AI_API_KEY is missing."
                ),
                hint=(
                    "Add AI_API_KEY=... to .env or provide AI_API_KEY as an "
                    "environment variable."
                ),
            )
        )

    if settings.ai_provider is AIProvider.LITELLM:
        litellm_available = _module_available(
            "agents.extensions.models.litellm_provider"
        )

        if not litellm_available:
            diagnostics.append(
                Diagnostic(
                    level="error",
                    message=(
                        "AI_PROVIDER=litellm is configured, but LiteLLM support "
                        "is not installed."
                    ),
                    hint=(
                        "Install LiteLLM support with:\n\n"
                        '  pip install "ai-incident-investigator[litellm]"'
                    ),
                )
            )

    if settings.session_secret_key == "change-this-development-secret":
        diagnostics.append(
            Diagnostic(
                level="warning",
                message="SESSION_SECRET_KEY is still using the development default.",
                hint=(
                    "Set a long random SESSION_SECRET_KEY before exposing "
                    "the service beyond local development."
                ),
            )
        )

    return diagnostics


def format_diagnostics(diagnostics: list[Diagnostic]) -> str:
    """Format diagnostics for a concise terminal report."""
    lines = ["AI Incident Investigator configuration check"]

    for item in diagnostics:
        marker = "ERROR" if item.level == "error" else "WARNING"

        lines.append("")
        lines.append(f"[{marker}] {item.message}")

        if item.hint:
            lines.append("")
            for hint_line in item.hint.splitlines():
                if hint_line:
                    lines.append(f"          {hint_line}")
                else:
                    lines.append("")

    if not diagnostics:
        lines.append("[OK] Configuration and optional dependencies look ready.")

    return "\n".join(lines)


def has_errors(diagnostics: list[Diagnostic]) -> bool:
    """Return True when at least one diagnostic is an error."""
    return any(item.level == "error" for item in diagnostics)