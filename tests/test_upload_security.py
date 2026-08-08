import pytest

from incident_investigator.security.upload import UploadValidationError, validate_log_upload

DEFAULTS = {
    "max_size_bytes": 1024,
    "allowed_extensions": {".log", ".txt"},
    "allowed_content_types": {"text/plain", "application/octet-stream"},
    "reject_binary_files": True,
}


def test_valid_upload_is_sanitized() -> None:
    upload = validate_log_upload(
        filename="../../service.log",
        content=b"INFO started",
        content_type="text/plain; charset=utf-8",
        **DEFAULTS,
    )
    assert upload.filename == "service.log"
    assert upload.content_type == "text/plain"


def test_binary_upload_is_rejected() -> None:
    with pytest.raises(UploadValidationError, match="Binary"):
        validate_log_upload(
            filename="dump.log",
            content=b"abc\x00def",
            content_type="application/octet-stream",
            **DEFAULTS,
        )


def test_extension_and_size_are_enforced() -> None:
    with pytest.raises(UploadValidationError, match="extension"):
        validate_log_upload(
            filename="archive.zip",
            content=b"data",
            content_type="application/octet-stream",
            **DEFAULTS,
        )
    with pytest.raises(UploadValidationError, match="upload limit"):
        validate_log_upload(
            filename="large.log",
            content=b"x" * 1025,
            content_type="text/plain",
            **DEFAULTS,
        )
