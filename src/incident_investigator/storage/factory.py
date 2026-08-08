from functools import lru_cache
from pathlib import Path

from incident_investigator.config import Settings, StorageBackend, get_settings
from incident_investigator.storage.local import LocalFilesystemLogStorage
from incident_investigator.storage.protocol import LogStorage
from incident_investigator.storage.s3 import S3LogStorage


def create_log_storage(settings: Settings) -> LogStorage:
    if settings.storage_backend is StorageBackend.LOCAL:
        return LocalFilesystemLogStorage(Path(settings.local_storage_path))
    if settings.storage_backend is StorageBackend.S3:
        if not settings.s3_bucket:
            raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3.")
        return S3LogStorage(
            bucket=settings.s3_bucket,
            prefix=settings.s3_prefix,
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            use_ssl=settings.s3_use_ssl,
        )
    raise ValueError(f"Unsupported storage backend: {settings.storage_backend}")


@lru_cache(maxsize=1)
def get_log_storage() -> LogStorage:
    return create_log_storage(get_settings())
