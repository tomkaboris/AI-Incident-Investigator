from pathlib import Path, PurePosixPath

from incident_investigator.archive.exceptions import UnsafeArchiveError


def safe_destination(base: Path, member_name: str) -> Path:
    normalized = member_name.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts:
        raise UnsafeArchiveError(f"Unsafe archive member path: {member_name}")
    destination = (base / Path(*pure.parts)).resolve()
    resolved_base = base.resolve()
    if destination != resolved_base and resolved_base not in destination.parents:
        raise UnsafeArchiveError(f"Archive member escapes destination: {member_name}")
    return destination
