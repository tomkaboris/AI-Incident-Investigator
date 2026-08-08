from datetime import UTC, datetime
from pathlib import Path

from incident_investigator.archive.indexer import index_artifact
from incident_investigator.archive.types import ExtractedArtifact


def test_indexer_detects_component_timestamp_and_error(tmp_path: Path):
    path = tmp_path / "dns.log"
    path.write_text("2026-07-25T12:00:00Z ERROR request-id=abcdef12 DNS timeout\n")
    artifact = ExtractedArtifact("network/dns.log", path, None, 0, path.stat().st_size, "x", False)
    events, _ = index_artifact(artifact, 0, datetime(2026, 7, 25, 12, 0, tzinfo=UTC))
    assert artifact.component == "network"
    assert artifact.earliest_timestamp is not None
    assert events and events[0].correlation_ids == ["abcdef12"]
