from pathlib import Path

from incident_investigator.config import Settings
from incident_investigator.preflight import collect_diagnostics, format_diagnostics


def test_missing_env_is_warning_not_error(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, ai_api_key="test-key")
    diagnostics = collect_diagnostics(settings, cwd=tmp_path)
    missing_env = [item for item in diagnostics if "No .env file found" in item.message]
    assert len(missing_env) == 1
    assert missing_env[0].level == "warning"


def test_missing_sqlite_extra_has_actionable_install_command(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(_env_file=None, ai_api_key="test-key")

    from incident_investigator import preflight

    real_available = preflight._module_available

    def fake_available(module_name: str) -> bool:
        if module_name == "aiosqlite":
            return False
        return real_available(module_name)

    monkeypatch.setattr(preflight, "_module_available", fake_available)
    report = format_diagnostics(collect_diagnostics(settings, cwd=tmp_path))
    assert "Database backend 'sqlite' is configured" in report
    assert 'pip install "ai-incident-investigator[sqlite]"' in report


def test_s3_extra_message_includes_database_extra(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        ai_api_key="test-key",
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
    assert 'pip install "ai-incident-investigator[sqlite,s3]"' in report
