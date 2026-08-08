import io
import zipfile
from pathlib import Path

import pytest

from incident_investigator.archive.exceptions import UnsafeArchiveError
from incident_investigator.archive.extractor import RecursiveArchiveExtractor
from incident_investigator.config import Settings


def make_zip(path: Path, files: dict[str, bytes]):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)


def test_nested_zip_extraction(tmp_path):
    nested = io.BytesIO()
    with zipfile.ZipFile(nested, "w") as zf:
        zf.writestr("network/dns.log", b"2026-07-25T12:00:00Z ERROR timeout")
    outer = tmp_path / "bundle.zip"
    make_zip(
        outer,
        {"app/app.log": b"2026-07-25T12:00:01Z ERROR failed", "nested.zip": nested.getvalue()},
    )
    settings = Settings(
        _env_file=None,
        ai_api_key="x",
        max_archive_depth=3,
        local_storage_path=str(tmp_path / "store"),
    )
    extractor = RecursiveArchiveExtractor(settings)
    artifacts = extractor.extract(outer, tmp_path / "out")
    assert any(a.original_path == "app/app.log" for a in artifacts)
    assert any(a.original_path == "network/dns.log" for a in artifacts)
    assert extractor.max_depth_reached == 1


def test_zip_path_traversal_rejected(tmp_path):
    archive = tmp_path / "bad.zip"
    make_zip(archive, {"../../escape.log": b"bad"})
    settings = Settings(_env_file=None, ai_api_key="x", local_storage_path=str(tmp_path / "store"))
    with pytest.raises(UnsafeArchiveError):
        RecursiveArchiveExtractor(settings).extract(archive, tmp_path / "out")
