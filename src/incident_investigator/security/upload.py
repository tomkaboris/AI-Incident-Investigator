from dataclasses import dataclass
from pathlib import PurePath


class UploadValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedLogUpload:
    filename: str
    content: bytes
    content_type: str


def validate_log_upload(
    *,
    filename: str | None,
    content: bytes,
    content_type: str | None,
    max_size_bytes: int,
    allowed_extensions: set[str],
    allowed_content_types: set[str],
    reject_binary_files: bool,
) -> ValidatedLogUpload:
    if not content:
        raise UploadValidationError("Uploaded log is empty.")
    if len(content) > max_size_bytes:
        raise UploadValidationError("Log file exceeds the configured upload limit.")

    safe_filename = PurePath(filename or "unknown.log").name
    extension = PurePath(safe_filename).suffix.lower()
    if allowed_extensions and extension not in allowed_extensions:
        raise UploadValidationError(f"Unsupported log file extension: {extension or '<none>'}.")

    normalized_content_type = (content_type or "application/octet-stream").split(";", maxsplit=1)[0]
    if allowed_content_types and normalized_content_type not in allowed_content_types:
        raise UploadValidationError(f"Unsupported content type: {normalized_content_type}.")

    if reject_binary_files and b"\x00" in content[:8192]:
        raise UploadValidationError("Binary files are not accepted as logs.")

    return ValidatedLogUpload(
        filename=safe_filename,
        content=content,
        content_type=normalized_content_type,
    )
