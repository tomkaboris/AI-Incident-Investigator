from typing import Protocol, runtime_checkable


@runtime_checkable
class LogStorage(Protocol):
    """Backend-neutral storage contract for uploaded log bytes."""

    @property
    def backend_name(self) -> str: ...

    async def save(self, *, key: str, content: bytes, content_type: str | None = None) -> None: ...

    async def read(self, *, key: str) -> bytes: ...

    async def delete(self, *, key: str) -> None: ...

    async def exists(self, *, key: str) -> bool: ...
