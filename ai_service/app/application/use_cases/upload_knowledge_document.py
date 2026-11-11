from dataclasses import dataclass
from hashlib import sha256
from json import dumps
from typing import BinaryIO
from uuid import UUID

from app.domain.entities.knowledge_document import StoredDocument, VerifiedDocumentMetadata
from app.domain.ports.knowledge_ingestion import KnowledgeRepository, SnapshotStore, UploadResult


@dataclass(frozen=True, slots=True)
class UploadCommand:
    file: BinaryIO
    filename: str
    metadata: VerifiedDocumentMetadata
    operator_ref: str
    idempotency_key: str | None = None


class UploadKnowledgeDocument:
    def __init__(self, repository: KnowledgeRepository, snapshots: SnapshotStore) -> None:
        self._repository = repository
        self._snapshots = snapshots

    async def execute(self, command: UploadCommand) -> UploadResult:
        snapshot = await self._snapshots.save(command.file, command.filename)
        metadata_fingerprint = dumps(
            {
                "title": command.metadata.title,
                "source_url": command.metadata.source_url,
                "bank_code": command.metadata.bank_code,
                "product_type": command.metadata.product_type,
                "effective_from": str(command.metadata.effective_from),
                "effective_to": str(command.metadata.effective_to),
                "last_updated": str(command.metadata.last_updated),
                "retrieved_at": command.metadata.retrieved_at.isoformat() if command.metadata.retrieved_at else None,
                "logical_document_id": str(command.metadata.logical_document_id) if command.metadata.logical_document_id else None,
                "reviewed_by": command.metadata.reviewed_by,
                "reviewed_at": command.metadata.reviewed_at.isoformat(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        fingerprint = sha256(f"{snapshot.sha256}:{metadata_fingerprint}".encode()).hexdigest()
        try:
            return await self._repository.register_upload(
                operator_ref=command.operator_ref,
                idempotency_key=command.idempotency_key,
                request_fingerprint=fingerprint,
                metadata=command.metadata,
                snapshot=snapshot,
            )
        except Exception:
            await self._snapshots.discard_if_unreferenced(snapshot.path)
            raise


class GetKnowledgeDocument:
    def __init__(self, repository: KnowledgeRepository) -> None:
        self._repository = repository

    async def execute(self, document_id: UUID) -> StoredDocument | None:
        return await self._repository.get_document(document_id)


class SetKnowledgeDocumentActive:
    def __init__(self, repository: KnowledgeRepository) -> None:
        self._repository = repository

    async def execute(self, document_id: UUID, is_active: bool) -> StoredDocument | None:
        return await self._repository.set_document_active(document_id, is_active)
