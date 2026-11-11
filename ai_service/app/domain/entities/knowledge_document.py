from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


class IngestionStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class VerifiedDocumentMetadata:
    title: str
    reviewed_by: str
    reviewed_at: datetime
    source_url: str | None = None
    bank_code: str | None = None
    product_type: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    last_updated: date | None = None
    retrieved_at: datetime | None = None
    logical_document_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class StoredDocument:
    id: UUID
    logical_document_id: UUID
    version_no: int
    title: str
    source_url: str | None
    content_sha256: str
    snapshot_path: str
    media_type: str
    size_bytes: int
    ingestion_status: IngestionStatus
    review_status: str = "approved"
    is_active: bool = True
    error_code: str | None = None
    http_status: int = 202
