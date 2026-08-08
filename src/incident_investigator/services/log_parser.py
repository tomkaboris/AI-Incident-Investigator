import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedLog:
    content: str
    original_line_count: int
    retained_line_count: int
    truncated: bool


IMPORTANT_PATTERNS = re.compile(
    r"""
    error|
    exception|
    traceback|
    failed|
    failure|
    fatal|
    timeout|
    denied|
    unauthorized|
    unavailable|
    out\sof\smemory|
    oom|
    killed|
    refused|
    cannot|
    couldn't
    """,
    re.IGNORECASE | re.VERBOSE,
)


def parse_log(content: str, max_characters: int = 50_000) -> ParsedLog:
    """Prepare a log for AI analysis while retaining useful context."""

    lines = content.splitlines()
    selected_indexes: set[int] = set()

    for index, line in enumerate(lines):
        if IMPORTANT_PATTERNS.search(line):
            start = max(0, index - 3)
            end = min(len(lines), index + 4)
            selected_indexes.update(range(start, end))

    if selected_indexes:
        selected_lines = [f"{index + 1}: {lines[index]}" for index in sorted(selected_indexes)]
    else:
        selected_lines = [f"{index + 1}: {line}" for index, line in enumerate(lines)]

    parsed_content = "\n".join(selected_lines)
    truncated = len(parsed_content) > max_characters

    if truncated:
        parsed_content = parsed_content[-max_characters:]

    return ParsedLog(
        content=parsed_content,
        original_line_count=len(lines),
        retained_line_count=len(selected_lines),
        truncated=truncated,
    )
