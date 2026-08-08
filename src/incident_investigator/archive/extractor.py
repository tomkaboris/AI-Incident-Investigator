import bz2
import gzip
import lzma
import tarfile
import zipfile
from hashlib import sha256
from pathlib import Path

from incident_investigator.archive.detector import content_type_for, is_archive_path
from incident_investigator.archive.exceptions import (
    ArchiveLimitError,
    UnsafeArchiveError,
    UnsupportedArchiveError,
)
from incident_investigator.archive.security import safe_destination
from incident_investigator.archive.types import ExtractedArtifact
from incident_investigator.config import Settings


def _copy_limited(source, destination, maximum_bytes: int) -> int:
    total = 0
    while True:
        chunk = source.read(1024 * 1024)
        if not chunk:
            return total
        total += len(chunk)
        if total > maximum_bytes:
            raise ArchiveLimitError("An extracted file exceeds the configured per-file limit.")
        destination.write(chunk)


class RecursiveArchiveExtractor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.total_size = 0
        self.file_count = 0
        self.max_depth_reached = 0

    def _account(self, size: int, compressed_size: int | None = None) -> None:
        if size > self.settings.max_single_extracted_file_size_bytes:
            raise ArchiveLimitError("An extracted file exceeds the configured per-file limit.")
        self.total_size += size
        self.file_count += 1
        if self.total_size > self.settings.max_archive_extracted_size_bytes:
            raise ArchiveLimitError("Archive extracted size limit exceeded.")
        if self.file_count > self.settings.max_archive_file_count:
            raise ArchiveLimitError("Archive file-count limit exceeded.")
        if (
            compressed_size
            and compressed_size > 0
            and size / compressed_size > self.settings.max_compression_ratio
        ):
            raise ArchiveLimitError("Suspicious archive compression ratio detected.")

    def extract(self, archive_path: Path, destination: Path) -> list[ExtractedArtifact]:
        artifacts = []
        self._extract_recursive(archive_path, destination, 0, None, artifacts)
        return artifacts

    def _extract_recursive(
        self,
        archive_path: Path,
        destination: Path,
        depth: int,
        source: str | None,
        artifacts: list[ExtractedArtifact],
    ) -> None:
        if depth > self.settings.max_archive_depth:
            raise ArchiveLimitError("Maximum nested archive depth exceeded.")
        self.max_depth_reached = max(self.max_depth_reached, depth)
        destination.mkdir(parents=True, exist_ok=True)
        extracted = self._extract_one(archive_path, destination)
        for path, original_name, compressed_size in extracted:
            if path.is_symlink() or not path.is_file():
                continue
            size = path.stat().st_size
            self._account(size, compressed_size)
            checksum = sha256(path.read_bytes()).hexdigest()
            nested = is_archive_path(path)
            artifact = ExtractedArtifact(
                original_path=original_name,
                absolute_path=path,
                source_archive_path=source or archive_path.name,
                depth=depth,
                size_bytes=size,
                checksum_sha256=checksum,
                is_archive=nested,
                content_type=content_type_for(path),
            )
            artifacts.append(artifact)
            if nested:
                nested_dir = destination / ("__nested_" + checksum[:12])
                try:
                    self._extract_recursive(path, nested_dir, depth + 1, original_name, artifacts)
                except UnsupportedArchiveError:
                    artifact.processing_status = "nested_extraction_failed"

    def _extract_one(self, archive_path: Path, destination: Path):
        name = archive_path.name.lower()
        output = []
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    mode = (info.external_attr >> 16) & 0o170000
                    if mode == 0o120000:
                        raise UnsafeArchiveError("Symbolic links are not allowed in ZIP archives.")
                    target = safe_destination(destination, info.filename)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if info.file_size > self.settings.max_single_extracted_file_size_bytes:
                        raise ArchiveLimitError(
                            "An extracted file exceeds the configured per-file limit."
                        )
                    if (
                        info.compress_size
                        and info.file_size / info.compress_size
                        > self.settings.max_compression_ratio
                    ):
                        raise ArchiveLimitError("Suspicious archive compression ratio detected.")
                    with zf.open(info) as src, target.open("wb") as dst:
                        _copy_limited(src, dst, self.settings.max_single_extracted_file_size_bytes)
                    output.append((target, info.filename, info.compress_size))
            return output
        if tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, "r:*") as tf:
                for member in tf.getmembers():
                    if member.isdir():
                        continue
                    if not member.isfile():
                        raise UnsafeArchiveError("Links and special TAR members are not allowed.")
                    target = safe_destination(destination, member.name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    src = tf.extractfile(member)
                    if src is None:
                        continue
                    if member.size > self.settings.max_single_extracted_file_size_bytes:
                        raise ArchiveLimitError(
                            "An extracted file exceeds the configured per-file limit."
                        )
                    with src, target.open("wb") as dst:
                        _copy_limited(src, dst, self.settings.max_single_extracted_file_size_bytes)
                    output.append((target, member.name, None))
            return output
        opener = None
        suffix = None
        if name.endswith(".gz"):
            opener = gzip.open
            suffix = ".gz"
        elif name.endswith(".bz2"):
            opener = bz2.open
            suffix = ".bz2"
        elif name.endswith(".xz"):
            opener = lzma.open
            suffix = ".xz"
        if opener:
            target = safe_destination(
                destination, archive_path.name[: -len(suffix)] or "decompressed.log"
            )
            with opener(archive_path, "rb") as src, target.open("wb") as dst:
                _copy_limited(src, dst, self.settings.max_single_extracted_file_size_bytes)
            return [(target, target.name, archive_path.stat().st_size)]
        raise UnsupportedArchiveError(f"Unsupported archive format: {archive_path.name}")
