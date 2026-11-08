import hashlib
from pathlib import Path

import pytest

from app.infrastructure.knowledge.document_extractor import LocalDocumentExtractor


@pytest.mark.parametrize("original_root", [r"D:\service\data\snapshots", "/old/container/snapshots"])
def test_extractor_reads_host_snapshot_from_container_mount(tmp_path: Path, original_root: str):
    body = "Verified loan conditions."
    checksum = hashlib.sha256(body.encode()).hexdigest()
    mounted = tmp_path / checksum[:2] / checksum
    mounted.parent.mkdir()
    mounted.write_text(body, encoding="utf-8")
    separator = "\\" if original_root.startswith("D:") else "/"
    stored_path = separator.join([original_root, checksum[:2], checksum])

    extractor = LocalDocumentExtractor(snapshot_root=tmp_path)

    assert extractor.extract(stored_path, "text/plain") == [(None, body)]


@pytest.mark.parametrize("stored_path", ["../../etc/passwd", r"D:\snapshots\invalid", "/tmp/" + "a" * 63])
def test_extractor_rejects_non_content_addressed_paths(tmp_path: Path, stored_path: str):
    extractor = LocalDocumentExtractor(snapshot_root=tmp_path)

    with pytest.raises(ValueError, match="invalid snapshot key"):
        extractor.extract(stored_path, "text/plain")
