from dataclasses import dataclass
from datetime import date
from typing import BinaryIO, Protocol
from uuid import UUID

from app.domain.entities.knowledge_chunk import KnowledgeChunk
from app.domain.entities.knowledge_document import StoredDocument, VerifiedDocumentMetadata


@dataclass(frozen=True, slots=True)
class Snapshot:
    path: str
    sha256: str
    size_bytes: int
    media_type: str
    original_filename: str


@dataclass(frozen=True, slots=True)
class UploadResult:
    document: StoredDocument
    created: bool


@dataclass(frozen=True, slots=True)
class IngestionJob:
    id: UUID
    document_id: UUID
    snapshot_path: str
    media_type: str
    expected_sha256: str
    effective_from: date | None = None
    effective_to: date | None = None


class SnapshotStore(Protocol):
    async def save(self, source: BinaryIO, filename: str) -> Snapshot: ...

    async def discard_if_unreferenced(self, path: str) -> None: ...


class KnowledgeRepository(Protocol):
    async def register_upload(
        self,
        *,
        operator_ref: str,
        idempotency_key: str | None,
        request_fingerprint: str,
        metadata: VerifiedDocumentMetadata,
        snapshot: Snapshot,
    ) -> UploadResult: ...

    async def get_document(self, document_id: UUID) -> StoredDocument | None: ...

    async def claim_ingestion(self, document_id: UUID) -> IngestionJob | None: ...

    async def publish_chunks(
        self,
        job: IngestionJob,
        chunks: list[KnowledgeChunk],
        embeddings: list[list[float]],
        *,
        embedding_model: str,
        embedding_version: str,
        effective_from: date | None,
        effective_to: date | None,
    ) -> None: ...

    async def fail_ingestion(self, job: IngestionJob, error_code: str) -> None: ...


class DocumentExtractor(Protocol):
    def extract(self, snapshot_path: str, media_type: str) -> list[tuple[int | None, str]]: ...


class TextEmbedder(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
