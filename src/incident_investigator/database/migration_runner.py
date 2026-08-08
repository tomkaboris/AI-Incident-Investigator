"""Database migration utilities bundled with the installed package."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from incident_investigator.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def build_alembic_config() -> Config:
    """Build an Alembic configuration that works from an installed wheel."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
    return config


def upgrade_database(revision: str = "head") -> None:
    """Upgrade the configured database to *revision*."""
    command.upgrade(build_alembic_config(), revision)
