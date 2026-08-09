from pathlib import Path

from incident_investigator.config import Settings
from incident_investigator.preflight import collect_diagnostics, format_diagnostics


def test_missing_env_is_warning_not_error(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, ai_api_key="test-key")
    diagnostics = collect_diagnostics(settings, cwd=tmp_path)
    missing_env = [item for item in diagnostics if "No .env file found" in item.message]
    assert len(missing_env) == 1
    assert missing_env[0].level == "warning"


def test_missing_default_database_extra_lists_all_supported_choices(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = Settings(_env_file=None, ai_api_key="test-key")

    from incident_investigator import preflight

    real_available = preflight._module_available

    def fake_available(module_name: str) -> bool:
        if module_name == "aiosqlite":
            return False
        return real_available(module_name)

    monkeypatch.setattr(preflight, "_module_available", fake_available)
    report = format_diagnostics(collect_diagnostics(settings, cwd=tmp_path))
    assert "No database backend was explicitly configured" in report
    assert 'pip install "ai-incident-investigator[sqlite]"' in report
    assert 'pip install "ai-incident-investigator[postgresql]"' in report
    assert 'pip install "ai-incident-investigator[mysql]"' in report


def test_explicit_postgresql_has_actionable_install_command(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        ai_api_key="test-key",
        database_url="postgresql+asyncpg://user:pass@localhost/incidents",
    )

    from incident_investigator import preflight

    monkeypatch.setattr(
        preflight,
        "_module_available",
        lambda module_name: module_name != "asyncpg",
    )
    report = format_diagnostics(collect_diagnostics(settings, cwd=tmp_path))
    assert "Database backend 'postgresql' is configured" in report
    assert 'pip install "ai-incident-investigator[postgresql]"' in report


def test_s3_extra_message_includes_database_extra(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        ai_api_key="test-key",
        database_url="mysql+aiomysql://user:pass@localhost/incidents",
        storage_backend="s3",
        s3_bucket="bucket",
    )

    from incident_investigator import preflight

    real_available = preflight._module_available

    def fake_available(module_name: str) -> bool:
        if module_name == "boto3":
            return False
        return real_available(module_name)

    monkeypatch.setattr(preflight, "_module_available", fake_available)
    report = format_diagnostics(collect_diagnostics(settings, cwd=tmp_path))
    assert 'pip install "ai-incident-investigator[mysql,s3]"' in report


def test_github_enabled_without_token_is_actionable(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        ai_api_key="test-key",
        github_enabled=True,
        github_base_url="https://ghe.example",
    )
    report = format_diagnostics(collect_diagnostics(settings, cwd=tmp_path))
    assert "GitHub source lookup is enabled, but GITHUB_TOKEN is missing" in report
