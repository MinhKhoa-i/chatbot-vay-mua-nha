from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True, slots=True)
class KnowledgeEvidence:
    """A chunk from an approved, currently effective source."""

    chunk_id: UUID
    document_id: UUID
    title: str
    source_url: str | None
    body: str
    score: float
    bank_code: str | None = None
    product_type: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeSearchQuery:
    text: str
    embedding: tuple[float, ...]
    limit: int = 5
    min_score: float = 0.15


@dataclass(frozen=True, slots=True)
class GroundedContext:
    evidence: tuple[KnowledgeEvidence, ...]
    prompt_context: str
    citations: tuple[str, ...]
