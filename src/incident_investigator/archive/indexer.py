import re
from datetime import UTC, datetime
from pathlib import Path

from incident_investigator.archive.detector import LOG_SUFFIXES, detect_component, detect_format
from incident_investigator.archive.types import ExtractedArtifact, TimelineEvent

TIMESTAMP_PATTERNS = [
    re.compile(
        r"(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
    ),
    re.compile(r"(?P<ts>\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:[.,]\d+)?)"),
]
SEVERITY = re.compile(
    r"\b(TRACE|DEBUG|INFO|NOTICE|WARN(?:ING)?|ERROR|FATAL|CRITICAL|SEVERE)\b", re.I
)
CORRELATION = re.compile(
    r"(?:trace|request|correlation|session|transaction|span)"
    r"[-_ ]?id[=: ]+[\"']?([A-Za-z0-9._:-]{6,128})",
    re.I,
)
IMPORTANT = re.compile(
    (
        r"error|exception|fail(?:ed|ure)?|fatal|critical|timeout|timed out|oom|"
        r"out of memory|crash|restart|unavailable|refused|denied|disconnect"
    ),
    re.I,
)


def decode_text(path: Path) -> tuple[str, str] | None:
    data = path.read_bytes()
    if b"\x00" in data[:8192]:
        return None
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    return None


def parse_timestamp(value: str, incident_year: int | None = None) -> datetime | None:
    clean = value.replace(",", ".")
    if clean.endswith("Z"):
        clean = clean[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(clean)
        return dt.replace(tzinfo=dt.tzinfo or UTC).astimezone(UTC)
    except ValueError:
        pass
    if re.match(r"\d{2}-\d{2} ", clean) and incident_year:
        try:
            return datetime.strptime(f"{incident_year}-{clean}", "%Y-%m-%d %H:%M:%S.%f").replace(
                tzinfo=UTC
            )
        except ValueError:
            try:
                return datetime.strptime(f"{incident_year}-{clean}", "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=UTC
                )
            except ValueError:
                return None
    return None


def index_artifact(
    artifact: ExtractedArtifact, artifact_index: int, incident_time: datetime | None
) -> tuple[list[TimelineEvent], str]:
    decoded = decode_text(artifact.absolute_path)
    if decoded is None:
        artifact.processing_status = "skipped_binary"
        return [], ""
    text, encoding = decoded
    artifact.encoding = encoding
    artifact.is_log_candidate = artifact.absolute_path.suffix.lower() in LOG_SUFFIXES or bool(
        IMPORTANT.search(text[:10000])
    )
    artifact.log_format = detect_format(artifact.absolute_path, text[:10000])
    artifact.component = detect_component(artifact.original_path, text[:10000])
    events = []
    timestamps = []
    year = incident_time.year if incident_time else None
    for number, line in enumerate(text.splitlines(), 1):
        match = next(
            (pattern.search(line) for pattern in TIMESTAMP_PATTERNS if pattern.search(line)), None
        )
        ts = parse_timestamp(match.group("ts"), year) if match else None
        if ts:
            timestamps.append(ts)
        if IMPORTANT.search(line) or (
            ts and incident_time and abs((ts - incident_time).total_seconds()) <= 3600
        ):
            sev = SEVERITY.search(line)
            events.append(
                TimelineEvent(
                    artifact_index=artifact_index,
                    path=artifact.original_path,
                    component=artifact.component or "unknown",
                    timestamp_utc=ts,
                    original_timestamp=match.group("ts") if match else None,
                    severity=sev.group(1).lower() if sev else None,
                    message=line[:2000],
                    line_number=number,
                    correlation_ids=CORRELATION.findall(line),
                )
            )
    if timestamps:
        artifact.earliest_timestamp = min(timestamps)
        artifact.latest_timestamp = max(timestamps)
    return events, text
