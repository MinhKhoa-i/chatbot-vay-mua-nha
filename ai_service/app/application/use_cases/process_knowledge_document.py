import math
from uuid import UUID

from app.application.services.knowledge_chunker import KnowledgeChunker
from app.domain.entities.knowledge_document import IngestionStatus
from app.domain.ports.knowledge_ingestion import DocumentExtractor, KnowledgeRepository, TextEmbedder


class ProcessKnowledgeDocument:
    def __init__(
        self,
        repository: KnowledgeRepository,
        extractor: DocumentExtractor,
        chunker: KnowledgeChunker,
        embedder: TextEmbedder,
        *,
        embedding_model: str,
        embedding_version: str = "mrl-prefix-1536-l2-v1",
        expected_dimensions: int = 1536,
    ) -> None:
        self._repository = repository
        self._extractor = extractor
        self._chunker = chunker
        self._embedder = embedder
        self._embedding_model = embedding_model
        self._embedding_version = embedding_version
        self._expected_dimensions = expected_dimensions

    async def execute(self, document_id: UUID) -> None:
        job = await self._repository.claim_ingestion(document_id)
        if job is None:
            return
        try:
            pages = self._extractor.extract(job.snapshot_path, job.media_type)
            chunks = self._chunker.chunk(
                document_id,
                pages,
                effective_from=job.effective_from.isoformat() if job.effective_from else None,
                effective_to=job.effective_to.isoformat() if job.effective_to else None,
            )
            if not chunks:
                raise ValueError("empty extraction")
            embeddings = await self._embedder.embed_documents([chunk.body for chunk in chunks])
            if len(embeddings) != len(chunks) or any(len(vector) != self._expected_dimensions for vector in embeddings):
                raise ValueError("embedding dimension or count mismatch")
            if any(not all(math.isfinite(value) for value in vector) for vector in embeddings):
                raise ValueError("embedding contains non-finite values")
            await self._repository.publish_chunks(
                job,
                chunks,
                embeddings,
                embedding_model=self._embedding_model,
                embedding_version=self._embedding_version,
                effective_from=job.effective_from,
                effective_to=job.effective_to,
            )
        except Exception as exc:
            error_code = "EXTRACTION_FAILED" if isinstance(exc, ValueError) else "INGESTION_UNAVAILABLE"
            await self._repository.fail_ingestion(job, error_code)
            raise RuntimeError(error_code) from exc
