from pathlib import Path

from incident_investigator.database.migration_runner import MIGRATIONS_DIR


def test_bundled_migrations_are_available() -> None:
    assert (MIGRATIONS_DIR / "env.py").is_file()
    assert (MIGRATIONS_DIR / "script.py.mako").is_file()
    assert any((MIGRATIONS_DIR / "versions").glob("*.py"))


def test_env_file_is_resolved_from_working_directory() -> None:
    from incident_investigator.config import Settings

    env_file = Settings.model_config.get("env_file")
    assert env_file == ".env"
    assert not Path(str(env_file)).is_absolute()
