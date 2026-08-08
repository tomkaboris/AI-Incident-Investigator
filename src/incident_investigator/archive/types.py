from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class ExtractedArtifact:
    original_path: str
    absolute_path: Path
    source_archive_path: str | None
    depth: int
    size_bytes: int
    checksum_sha256: str
    is_archive: bool
    content_type: str | None = None
    component: str | None = None
    log_format: str | None = None
    encoding: str | None = None
    earliest_timestamp: datetime | None = None
    latest_timestamp: datetime | None = None
    is_log_candidate: bool = False
    processing_status: str = "indexed"


@dataclass(slots=True)
class TimelineEvent:
    artifact_index: int
    path: str
    component: str
    timestamp_utc: datetime | None
    original_timestamp: str | None
    severity: str | None
    message: str
    line_number: int | None
    correlation_ids: list[str] = field(default_factory=list)
