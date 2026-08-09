"""Friendly startup diagnostics for CLI users.

The checks in this module deliberately avoid changing the configuration model itself.
That keeps programmatic, Docker, and CI usage backward compatible while giving
``incident-investigator`` users actionable errors before optional imports fail.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from incident_investigator.config import AIProvider, Settings, StorageBackend


@dataclass(frozen=True, slots=True)
class Diagnostic:
    level: str
    message: str
    hint: str | None = None


_DATABASE_DRIVERS: dict[str, tuple[str, str]] = {
    "sqlite": ("aiosqlite", 'pip install "ai-incident-investigator[sqlite]"'),
    "postgresql": ("asyncpg", 'pip install "ai-incident-investigator[postgresql]"'),
    "postgres": ("asyncpg", 'pip install "ai-incident-investigator[postgresql]"'),
    "mysql": ("aiomysql", 'pip install "ai-incident-investigator[mysql]"'),
    "mariadb": ("aiomysql", 'pip install "ai-incident-investigator[mysql]"'),
}


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _database_backend(database_url: str) -> str:
    scheme = urlsplit(database_url).scheme.lower()
    return scheme.split("+", maxsplit=1)[0]


def collect_diagnostics(settings: Settings, *, cwd: Path | None = None) -> list[Diagnostic]:
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
                    "Create .env in this directory, or provide the same settings through "
                    "environment variables (useful for Docker/CI). See README Configuration."
                ),
            )
        )

    backend = _database_backend(settings.database_url)
    driver_info = _DATABASE_DRIVERS.get(backend)
    if driver_info:
        module_name, install_command = driver_info
        if not _module_available(module_name):
            diagnostics.append(
                Diagnostic(
                    level="error",
                    message=(
                        f"Database backend '{backend}' is configured, but its Python driver "
                        f"'{module_name}' is not installed."
                    ),
                    hint=f"Install the matching database extra: {install_command}",
                )
            )

    if settings.storage_backend is StorageBackend.S3 and not _module_available("boto3"):
        diagnostics.append(
            Diagnostic(
                level="error",
                message=(
                    "S3 storage is configured, but the optional dependency "
                    "'boto3' is not installed."
                ),
                hint=(
                    "Install S3 together with your database extra, for example: "
                    'pip install "ai-incident-investigator[sqlite,s3]"'
                ),
            )
        )

    if settings.ai_provider is AIProvider.OPENAI and not settings.ai_api_key:
        diagnostics.append(
            Diagnostic(
                level="error",
                message="AI_PROVIDER=openai is configured, but AI_API_KEY is missing.",
                hint="Add AI_API_KEY=... to .env or provide AI_API_KEY as an environment variable.",
            )
        )

    if settings.ai_provider is AIProvider.LITELLM:
        try:
            litellm_available = _module_available("agents.extensions.models.litellm_provider")
        except ModuleNotFoundError:
            litellm_available = False
        if not litellm_available:
            diagnostics.append(
                Diagnostic(
                    level="error",
                    message=(
                        "AI_PROVIDER=litellm is configured, but LiteLLM support "
                        "is not installed."
                    ),
                    hint='Install it with: pip install "ai-incident-investigator[litellm]"',
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
        lines.append(f"[{marker}] {item.message}")
        if item.hint:
            lines.append(f"          {item.hint}")
    if not diagnostics:
        lines.append("[OK] Configuration and optional dependencies look ready.")
    return "\n".join(lines)


def has_errors(diagnostics: list[Diagnostic]) -> bool:
    return any(item.level == "error" for item in diagnostics)
