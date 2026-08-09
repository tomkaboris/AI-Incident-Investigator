from __future__ import annotations

import re
from pathlib import PurePath

from incident_investigator.source_analysis.models import LogSourceHint

_PYTHON_FRAME = re.compile(
    r'File\s+["\'](?P<path>[^"\']+)["\'],\s+line\s+(?P<line>\d+)(?:,\s+in\s+(?P<func>[^\s]+))?'
)
_JAVA_FRAME = re.compile(
    r"\bat\s+[\w.$]+\.(?P<func>[\w$<>]+)\((?P<file>[\w.$-]+\.(?:java|kt)):(?P<line>\d+)\)"
)
_GENERIC_LOCATION = re.compile(
    r"(?P<path>(?:[A-Za-z]:)?[^\s:'\"<>|]+\."
    r"(?:py|java|kt|kts|c|cc|cpp|cxx|h|hpp|go|rs|js|jsx|ts|tsx|rb|php|cs|scala|sh|"
    r"groovy|gradle|xml|yaml|yml)):(?P<line>\d+)"
)
_ERROR_MARKERS = (
    " error ",
    "error:",
    "exception",
    "fatal",
    "failed",
    "failure",
    "traceback",
    "assertionerror",
)
_TIMESTAMP_PREFIX = re.compile(
    r"^\s*(?:\d{4}[-/]\d{2}[-/]\d{2}[T\s][0-9:.,+-Z]+\s+|\[[^\]]+\]\s*)"
)
_LEVEL_PREFIX = re.compile(r"^(?:DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL)\s*[:|-]?\s*", re.I)


def _filename(path: str | None) -> str | None:
    if not path:
        return None
    normalized = path.replace("\\", "/")
    return PurePath(normalized).name or None


def extract_source_hints(log_text: str, *, max_hints: int = 8) -> list[LogSourceHint]:
    """Extract concrete file/line/function hints from common stack-trace formats."""
    hints: list[LogSourceHint] = []
    seen: set[tuple[str | None, int | None, str | None]] = set()

    for raw_line in log_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        python_match = _PYTHON_FRAME.search(line)
        if python_match:
            path = python_match.group("path")
            hint = LogSourceHint(
                path=path,
                filename=_filename(path),
                function=python_match.group("func"),
                line_number=int(python_match.group("line")),
                excerpt=line[:500],
                confidence=0.95,
            )
            key = (hint.path, hint.line_number, hint.function)
            if key not in seen:
                hints.append(hint)
                seen.add(key)

        java_match = _JAVA_FRAME.search(line)
        if java_match:
            filename = java_match.group("file")
            hint = LogSourceHint(
                path=filename,
                filename=filename,
                function=java_match.group("func"),
                line_number=int(java_match.group("line")),
                excerpt=line[:500],
                confidence=0.9,
            )
            key = (hint.path, hint.line_number, hint.function)
            if key not in seen:
                hints.append(hint)
                seen.add(key)

        for match in _GENERIC_LOCATION.finditer(line):
            path = match.group("path").strip("()[]{}")
            hint = LogSourceHint(
                path=path,
                filename=_filename(path),
                line_number=int(match.group("line")),
                excerpt=line[:500],
                confidence=0.8,
            )
            key = (hint.path, hint.line_number, hint.function)
            if key not in seen:
                hints.append(hint)
                seen.add(key)

        if len(hints) >= max_hints:
            break

    return hints[:max_hints]


def extract_error_search_terms(log_text: str, *, max_terms: int = 6) -> list[str]:
    """Extract stable error-message fragments suitable for source-code search."""
    terms: list[str] = []
    seen: set[str] = set()

    for raw_line in reversed(log_text.splitlines()):
        lowered = f" {raw_line.lower()} "
        if not any(marker in lowered for marker in _ERROR_MARKERS):
            continue

        cleaned = _TIMESTAMP_PREFIX.sub("", raw_line.strip())
        cleaned = _LEVEL_PREFIX.sub("", cleaned).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\b0x[0-9a-fA-F]+\b", "", cleaned)
        cleaned = re.sub(r"\b\d{5,}\b", "", cleaned)
        cleaned = cleaned.strip(" :-|")

        if len(cleaned) < 12:
            continue
        if len(cleaned) > 180:
            cleaned = cleaned[:180].rsplit(" ", 1)[0]

        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        terms.append(cleaned)
        if len(terms) >= max_terms:
            break

    return terms
