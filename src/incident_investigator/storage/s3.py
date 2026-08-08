import asyncio
from typing import Any

from incident_investigator.storage.exceptions import LogNotFoundError, LogStorageError


class S3LogStorage:
    """S3-compatible storage supporting AWS S3, MinIO, and compatible services."""

    backend_name = "s3"

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str = "logs",
        endpoint_url: str | None = None,
        region_name: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        use_ssl: bool = True,
    ) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise LogStorageError(
                "S3 storage requires the optional dependency: "
                'pip install "ai-incident-investigator[s3]"'
            ) from exc

        self._bucket = bucket
        self._prefix = prefix.strip("/")
        kwargs: dict[str, Any] = {
            "endpoint_url": endpoint_url,
            "region_name": region_name,
            "aws_access_key_id": access_key_id,
            "aws_secret_access_key": secret_access_key,
            "use_ssl": use_ssl,
        }
        client_options = {key: value for key, value in kwargs.items() if value is not None}
        self._client = boto3.client("s3", **client_options)

    def _object_key(self, key: str) -> str:
        clean_key = key.lstrip("/")
        return f"{self._prefix}/{clean_key}" if self._prefix else clean_key

    async def save(self, *, key: str, content: bytes, content_type: str | None = None) -> None:
        params: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": self._object_key(key),
            "Body": content,
        }
        if content_type:
            params["ContentType"] = content_type
        await asyncio.to_thread(self._client.put_object, **params)

    async def read(self, *, key: str) -> bytes:
        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                Bucket=self._bucket,
                Key=self._object_key(key),
            )
        except self._client.exceptions.NoSuchKey as exc:
            raise LogNotFoundError(f"Stored log was not found: {key}") from exc
        except Exception as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if error_code in {"NoSuchKey", "404", "NotFound"}:
                raise LogNotFoundError(f"Stored log was not found: {key}") from exc
            raise LogStorageError("Unable to read object from S3-compatible storage.") from exc
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, *, key: str) -> None:
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self._bucket,
            Key=self._object_key(key),
        )

    async def exists(self, *, key: str) -> bool:
        try:
            await asyncio.to_thread(
                self._client.head_object,
                Bucket=self._bucket,
                Key=self._object_key(key),
            )
            return True
        except Exception as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if error_code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise LogStorageError("Unable to inspect object in S3-compatible storage.") from exc
