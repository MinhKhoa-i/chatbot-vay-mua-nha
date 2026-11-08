import re
from pathlib import Path, PureWindowsPath


MAX_EXTRACTED_CHARS = 5_000_000


class LocalDocumentExtractor:
    def __init__(self, *, snapshot_root: Path | None = None, max_pages: int = 500,
                 max_extracted_chars: int = MAX_EXTRACTED_CHARS) -> None:
        self._snapshot_root = snapshot_root.resolve() if snapshot_root is not None else None
        self._max_pages = max_pages
        self._max_extracted_chars = max_extracted_chars

    def _resolve_snapshot(self, snapshot_path: str) -> Path:
        if self._snapshot_root is None:
            return Path(snapshot_path)
        # Stored absolute paths can originate from Windows or a different container.
        # Only use the content-addressed filename, never traverse outside the mount.
        checksum = PureWindowsPath(snapshot_path).name
        if re.fullmatch(r"[0-9a-f]{64}", checksum) is None:
            raise ValueError("invalid snapshot key")
        path = (self._snapshot_root / checksum[:2] / checksum).resolve()
        if not path.is_relative_to(self._snapshot_root):
            raise ValueError("snapshot outside configured root")
        return path

    def extract(self, snapshot_path: str, media_type: str) -> list[tuple[int | None, str]]:
        path = self._resolve_snapshot(snapshot_path)
        if media_type == "application/pdf":
            return self._extract_pdf(path)
        if media_type in {"text/plain", "text/markdown"}:
            text = path.read_text(encoding="utf-8", errors="strict")
            self._validate_text(text)
            return [(None, text)]
        raise ValueError("unsupported media type")

    def _extract_pdf(self, path: Path) -> list[tuple[int | None, str]]:
        from pypdf import PdfReader

        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted or len(reader.pages) > self._max_pages:
            raise ValueError("pdf rejected")
        pages: list[tuple[int | None, str]] = []
        total_chars = 0
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text(extraction_mode="layout") or ""
            self._validate_text(text, allow_empty=True)
            total_chars += len(text)
            if total_chars > self._max_extracted_chars:
                raise ValueError("extracted text limit")
            if text.strip():
                pages.append((index, text))
        if not pages:
            raise ValueError("pdf has no extractable text")
        return pages

    def _validate_text(self, text: str, *, allow_empty: bool = False) -> None:
        if len(text) > self._max_extracted_chars or "\x00" in text:
            raise ValueError("text rejected")
        if not allow_empty and not text.strip():
            raise ValueError("empty text")
        if re.search(r"<\s*(script|html|iframe)\b", text, re.IGNORECASE):
            raise ValueError("HTML not allowed")
