import asyncio
import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import BinaryIO

from app.domain.ports.knowledge_ingestion import Snapshot


MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class UploadRejected(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class LocalSnapshotStore:
    def __init__(self, root: Path, max_bytes: int = MAX_UPLOAD_BYTES) -> None:
        self._root = root.resolve()
        self._max_bytes = max_bytes
        self._root.mkdir(parents=True, exist_ok=True)

    async def save(self, source: object, filename: str) -> Snapshot:
        stream = getattr(source, "file", source)
        position = stream.tell()
        try:
            return await asyncio.to_thread(self._save_sync, source, filename)
        finally:
            stream.seek(position)

    def _save_sync(self, source: object, filename: str) -> Snapshot:
        suffix = Path(filename).suffix.lower()
        media_type = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown"}.get(suffix)
        if media_type is None:
            raise UploadRejected("UNSUPPORTED_FILE_TYPE")

        stream: BinaryIO = getattr(source, "file", source)
        fd, temp_name = tempfile.mkstemp(prefix=".upload-", dir=self._root)
        temp_path = Path(temp_name)
        digest = hashlib.sha256()
        size = 0
        prefix = b""
        try:
            with os.fdopen(fd, "wb") as target:
                while True:
                    block = stream.read(64 * 1024)
                    if not block:
                        break
                    size += len(block)
                    if size > self._max_bytes:
                        raise UploadRejected("FILE_TOO_LARGE")
                    if len(prefix) < 8:
                        prefix += block[: 8 - len(prefix)]
                    digest.update(block)
                    target.write(block)
                target.flush()
                os.fsync(target.fileno())
            if size == 0:
                raise UploadRejected("EMPTY_FILE")
            self._validate_content(suffix, prefix, temp_path, max_bytes=self._max_bytes)
            checksum = digest.hexdigest()
            destination = self._root / checksum[:2] / checksum
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                temp_path.unlink(missing_ok=True)
            else:
                try:
                    os.link(temp_path, destination)
                except FileExistsError:
                    pass
                finally:
                    temp_path.unlink(missing_ok=True)
            return Snapshot(str(destination), checksum, size, media_type, Path(filename).name[:255])
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    async def discard_if_unreferenced(self, path: str) -> None:
        # Content-addressed snapshots may be shared; cleanup is delegated to a DB-aware GC.
        return None

    @staticmethod
    def _validate_content(suffix: str, prefix: bytes, path: Path, *, max_bytes: int) -> None:
        if suffix == ".pdf":
            if not prefix.startswith(b"%PDF-"):
                raise UploadRejected("INVALID_FILE_CONTENT")
            try:
                from pypdf import PdfReader

                reader = PdfReader(str(path), strict=True)
                if reader.is_encrypted:
                    raise UploadRejected("ENCRYPTED_PDF")
                if len(reader.pages) > min(500, max_bytes // 1024):
                    raise UploadRejected("PDF_PAGE_LIMIT")
            except UploadRejected:
                raise
            except Exception as exc:
                raise UploadRejected("INVALID_FILE_CONTENT") from exc
            return
        try:
            text = path.read_bytes().decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise UploadRejected("INVALID_UTF8") from exc
        if not text.strip() or "\x00" in text:
            raise UploadRejected("INVALID_FILE_CONTENT")
        if re.search(r"<\s*(script|html|iframe)\b", text, re.IGNORECASE):
            raise UploadRejected("HTML_NOT_ALLOWED")
