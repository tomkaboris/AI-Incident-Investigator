from pathlib import Path

import pytest

from incident_investigator.config import Settings
from incident_investigator.integrations.github import (
    GitHubFile,
    GitHubIntegrationError,
    GitHubSearchHit,
)
from incident_investigator.source_analysis.extractor import extract_source_hints
from incident_investigator.source_analysis.models import SourceAnalysisStatus
from incident_investigator.source_analysis.service import analyze_source_location


def test_extracts_python_stack_trace_location() -> None:
    log = 'File "/srv/app/device_setup.py", line 219, in update_available\nRuntimeError: failed'
    hints = extract_source_hints(log)
    assert hints[0].filename == "device_setup.py"
    assert hints[0].line_number == 219
    assert hints[0].function == "update_available"


def test_extracts_java_stack_trace_location() -> None:
    log = "at com.example.DeviceManager.update(DeviceManager.java:88)"
    hints = extract_source_hints(log)
    assert hints[0].filename == "DeviceManager.java"
    assert hints[0].line_number == 88
    assert hints[0].function == "update"


@pytest.mark.asyncio
async def test_disabled_github_returns_log_inference() -> None:
    settings = Settings(_env_file=None, github_enabled=False)
    log = 'File "/srv/app/device_setup.py", line 12, in update\nRuntimeError: failed'
    result = await analyze_source_location(log, settings)
    assert result.status is SourceAnalysisStatus.INFERRED_FROM_LOG
    assert result.provider == "log"
    assert result.path == "/srv/app/device_setup.py"
    assert result.start_line == 12


class FakeGitHubClient:
    async def search_code(self, term: str) -> list[GitHubSearchHit]:
        assert term
        return [
            GitHubSearchHit(
                owner="example",
                repository="device-lib",
                path="src/device_setup.py",
                name="device_setup.py",
                html_url="https://ghe.example/example/device-lib/blob/main/src/device_setup.py",
            )
        ]

    async def get_file(self, **_) -> GitHubFile:
        content = "\n".join(
            [
                "def helper():",
                "    pass",
                "",
                "def update_available():",
                '    logger.error("No updates available")',
                "    return False",
            ]
        )
        return GitHubFile(
            owner="example",
            repository="device-lib",
            path="src/device_setup.py",
            content=content,
            sha="blob-sha",
            html_url="https://ghe.example/example/device-lib/blob/main/src/device_setup.py",
        )


@pytest.mark.asyncio
async def test_github_verifies_source_location() -> None:
    settings = Settings(
        _env_file=None,
        github_enabled=True,
        github_token="secret-token",
        github_base_url="https://ghe.example",
        github_context_lines=5,
    )
    log = (
        'File "/app/src/device_setup.py", line 5, in update_available\n'
        "ERROR No updates available"
    )
    result = await analyze_source_location(log, settings, client=FakeGitHubClient())
    assert result.status is SourceAnalysisStatus.RESOLVED
    assert result.repository == "device-lib"
    assert result.path == "src/device_setup.py"
    assert result.source_url is not None
    assert "No updates available" in (result.snippet or "")
    assert result.confidence >= 0.8


class FailingGitHubClient:
    async def search_code(self, term: str):
        raise GitHubIntegrationError("GHE unavailable")


@pytest.mark.asyncio
async def test_github_failure_keeps_log_fallback() -> None:
    settings = Settings(
        _env_file=None,
        github_enabled=True,
        github_token="secret-token",
        github_base_url="https://ghe.example",
    )
    log = 'File "/app/service.py", line 44, in run\nERROR request failed'
    result = await analyze_source_location(log, settings, client=FailingGitHubClient())
    assert result.status is SourceAnalysisStatus.LOOKUP_FAILED
    assert result.path == "/app/service.py"
    assert result.lookup_message == "GHE unavailable"


def test_github_client_derives_enterprise_api_url() -> None:
    from incident_investigator.integrations.github import GitHubClient

    settings = Settings(
        _env_file=None,
        github_enabled=True,
        github_token="secret-token",
        github_base_url="https://ghe.example",
    )
    client = GitHubClient.from_settings(settings)
    assert client.api_url == "https://ghe.example/api/v3"


def test_github_client_derives_github_com_api_url() -> None:
    from incident_investigator.integrations.github import GitHubClient

    settings = Settings(
        _env_file=None,
        github_enabled=True,
        github_token="secret-token",
        github_base_url="https://github.com",
    )
    client = GitHubClient.from_settings(settings)
    assert client.api_url == "https://api.github.com"


def test_source_analysis_is_not_part_of_agent_output_schema() -> None:
    from incident_investigator.models.archive import ArchiveIncidentAnalysis
    from incident_investigator.models.incident import IncidentAnalysis
    from incident_investigator.models.orchestration import OrchestratedInvestigation

    assert "source_analysis" not in IncidentAnalysis.model_json_schema()["properties"]
    assert "source_analysis" not in OrchestratedInvestigation.model_json_schema()["properties"]
    assert "source_analysis" not in ArchiveIncidentAnalysis.model_json_schema()["properties"]
