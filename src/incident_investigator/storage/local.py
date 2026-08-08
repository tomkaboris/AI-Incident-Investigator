import asyncio
from pathlib import Path

from incident_investigator.storage.exceptions import LogNotFoundError, LogStorageError


class LocalFilesystemLogStorage:
    """Store logs below a configured directory without allowing path traversal."""

    backend_name = "local"

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path.resolve()
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_key(self, key: str) -> Path:
        candidate = (self._base_path / key).resolve()
        if candidate != self._base_path and self._base_path not in candidate.parents:
            raise LogStorageError("Storage key resolves outside the configured directory.")
        return candidate

    async def save(self, *, key: str, content: bytes, content_type: str | None = None) -> None:
        del content_type
        path = self._resolve_key(key)

        def write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = path.with_suffix(path.suffix + ".tmp")
            temporary_path.write_bytes(content)
            temporary_path.replace(path)

        await asyncio.to_thread(write)

    async def read(self, *, key: str) -> bytes:
        path = self._resolve_key(key)
        if not await asyncio.to_thread(path.is_file):
            raise LogNotFoundError(f"Stored log was not found: {key}")
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, *, key: str) -> None:
        path = self._resolve_key(key)

        def remove() -> None:
            try:
                path.unlink()
            except FileNotFoundError:
                return
            parent = path.parent
            while parent != self._base_path:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent

        await asyncio.to_thread(remove)

    async def exists(self, *, key: str) -> bool:
        return await asyncio.to_thread(self._resolve_key(key).is_file)
