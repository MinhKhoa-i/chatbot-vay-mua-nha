from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    document_id: UUID
    ordinal: int
    body: str
    body_sha256: str
    page: int | None = None
    section: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
