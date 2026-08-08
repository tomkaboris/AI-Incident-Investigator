from pathlib import Path

import pytest

from incident_investigator.storage.exceptions import (
    LogIntegrityError,
    LogNotFoundError,
    LogStorageError,
)
from incident_investigator.storage.local import LocalFilesystemLogStorage
from incident_investigator.storage.service import calculate_sha256, read_verified_log


@pytest.mark.asyncio
async def test_local_storage_round_trip(tmp_path: Path) -> None:
    storage = LocalFilesystemLogStorage(tmp_path)
    await storage.save(key="ab/test.log", content=b"hello", content_type="text/plain")

    assert await storage.exists(key="ab/test.log") is True
    assert await storage.read(key="ab/test.log") == b"hello"

    await storage.delete(key="ab/test.log")
    assert await storage.exists(key="ab/test.log") is False
    with pytest.raises(LogNotFoundError):
        await storage.read(key="ab/test.log")


def test_local_storage_rejects_path_traversal(tmp_path: Path) -> None:
    storage = LocalFilesystemLogStorage(tmp_path)
    with pytest.raises(LogStorageError):
        storage._resolve_key("../../secret")


@pytest.mark.asyncio
async def test_read_verified_log_detects_corruption(tmp_path: Path) -> None:
    storage = LocalFilesystemLogStorage(tmp_path)
    await storage.save(key="incident.log", content=b"changed")

    class Record:
        id = "incident-id"
        log_storage_key = "incident.log"
        log_checksum_sha256 = calculate_sha256(b"original")

    with pytest.raises(LogIntegrityError):
        await read_verified_log(Record(), storage)  # type: ignore[arg-type]
