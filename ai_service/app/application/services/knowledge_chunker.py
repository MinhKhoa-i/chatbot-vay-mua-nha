import hashlib
import re
import unicodedata
from collections.abc import Iterable, Sequence
from typing import Protocol
from uuid import UUID

from app.domain.entities.knowledge_chunk import KnowledgeChunk


class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]: ...

    def decode(self, tokens: list[int]) -> str: ...


class KnowledgeChunker:
    """NFC normalize and split extracted pages into bounded, overlapping chunks."""

    def __init__(self, tokenizer: Tokenizer, max_tokens: int = 500, overlap_tokens: int = 80) -> None:
        if max_tokens < 1 or not 0 <= overlap_tokens < max_tokens:
            raise ValueError("Invalid chunk token limits")
        self._tokenizer = tokenizer
        self._max_tokens = max_tokens
        self._overlap_tokens = overlap_tokens

    def chunk(
        self,
        document_id: UUID,
        pages: Sequence[tuple[int | None, str]],
        *,
        effective_from: str | None = None,
        effective_to: str | None = None,
    ) -> list[KnowledgeChunk]:
        output: list[KnowledgeChunk] = []
        for page, text in pages:
            normalized = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
            for section, section_text in self._sections(normalized):
                tokens = self._tokenizer.encode(section_text)
                start = 0
                while start < len(tokens):
                    end = min(start + self._max_tokens, len(tokens))
                    body = self._tokenizer.decode(tokens[start:end]).strip()
                    if body:
                        output.append(
                            KnowledgeChunk(
                                document_id=document_id,
                                ordinal=len(output),
                                body=body,
                                body_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
                                page=page,
                                section=section,
                                effective_from=effective_from,
                                effective_to=effective_to,
                            )
                        )
                    if end == len(tokens):
                        break
                    start = end - self._overlap_tokens
        return output

    @staticmethod
    def _sections(text: str) -> Iterable[tuple[str | None, str]]:
        current_heading: str | None = None
        buffer: list[str] = []
        for line in text.splitlines():
            match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
            if match:
                if buffer:
                    yield current_heading, "\n".join(buffer).strip()
                    buffer.clear()
                current_heading = match.group(2).strip()
                buffer.append(line)
            else:
                buffer.append(line)
        if buffer:
            body = "\n".join(buffer).strip()
            if body:
                yield current_heading, body
