from hashlib import sha256
from pathlib import PurePath

from incident_investigator.database.models import IncidentRecord
from incident_investigator.storage.exceptions import LogIntegrityError
from incident_investigator.storage.protocol import LogStorage


def calculate_sha256(content: bytes) -> str:
    return sha256(content).hexdigest()


def build_storage_key(*, incident_id: str, filename: str) -> str:
    suffix = PurePath(filename).suffix.lower()
    safe_suffix = suffix if suffix and len(suffix) <= 16 else ".log"
    return f"{incident_id[:2]}/{incident_id}/{incident_id}{safe_suffix}"


async def read_verified_log(record: IncidentRecord, storage: LogStorage) -> bytes:
    content = await storage.read(key=record.log_storage_key)
    actual_checksum = calculate_sha256(content)
    if actual_checksum != record.log_checksum_sha256:
        raise LogIntegrityError(
            f"Checksum mismatch for incident {record.id}: expected "
            f"{record.log_checksum_sha256}, received {actual_checksum}."
        )
    return content
