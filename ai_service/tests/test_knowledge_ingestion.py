import asyncio
import hashlib
import io
import math
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.services.knowledge_chunker import KnowledgeChunker
from app.application.use_cases.process_knowledge_document import ProcessKnowledgeDocument
from app.application.use_cases.upload_knowledge_document import UploadCommand, UploadKnowledgeDocument
from app.domain.entities.knowledge_document import IngestionStatus, StoredDocument, VerifiedDocumentMetadata
from app.domain.ports.knowledge_ingestion import IngestionJob, UploadResult
from app.infrastructure.knowledge.local_snapshot_store import LocalSnapshotStore, UploadRejected
from app.presentation.api.knowledge_schemas import (
    KnowledgeDocumentResponse,
    UpdateKnowledgeActivation,
    UploadMetadata,
)


class WordTokenizer:
    def encode(self, text: str) -> list[str]:
        return text.split()

    def decode(self, tokens: list[str]) -> str:
        return " ".join(tokens)


class FakeRepository:
    def __init__(self):
        self.upload = None
        self.chunks = None
        self.failure = None

    async def register_upload(self, **kwargs):
        self.upload = kwargs
        snapshot = kwargs["snapshot"]
        document = StoredDocument(uuid4(), uuid4(), 1, kwargs["metadata"].title,
                                  kwargs["metadata"].source_url, snapshot.sha256, snapshot.path,
                                  snapshot.media_type, snapshot.size_bytes, IngestionStatus.QUEUED)
        return UploadResult(document, True)

    async def get_document(self, _document_id):
        return None

    async def claim_ingestion(self, document_id):
        return IngestionJob(uuid4(), document_id, "snapshot", "text/plain", "a" * 64)

    async def publish_chunks(self, job, chunks, embeddings, **kwargs):
        self.chunks = (job, chunks, embeddings, kwargs)

    async def fail_ingestion(self, job, error_code):
        self.failure = (job, error_code)


def test_activation_schema_requires_a_strict_boolean():
    assert UpdateKnowledgeActivation(is_active=False).is_active is False
    with pytest.raises(ValueError):
        UpdateKnowledgeActivation(is_active="false")


def test_document_response_includes_activation_state():
    document = StoredDocument(
        uuid4(), uuid4(), 1, "Terms", None, "a" * 64, "/snapshot", "text/markdown",
        12, IngestionStatus.PUBLISHED, is_active=False,
    )

    response = KnowledgeDocumentResponse.from_domain(document)

    assert response.is_active is False


def test_metadata_requires_verified_operator_review_and_safe_url():
    metadata = UploadMetadata(
        title="Terms", verified=True, reviewed_by="reviewer",
        reviewed_at=datetime.now(timezone.utc), source_url="https://example.org/doc",
        effective_from=date(2026, 1, 1),
    )
    assert metadata.to_domain().source_url == "https://example.org/doc"
    with pytest.raises(ValueError):
        UploadMetadata(title="bad", verified=False, reviewed_by="r",
                       reviewed_at=datetime.now(timezone.utc))
    with pytest.raises(ValueError):
        UploadMetadata(title="bad", verified=True, reviewed_by="r",
                       reviewed_at=datetime.now(timezone.utc), source_url="file:///etc/passwd")


def test_chunking_preserves_page_heading_and_expected_overlap():
    chunker = KnowledgeChunker(WordTokenizer(), max_tokens=5, overlap_tokens=2)
    chunks = chunker.chunk(uuid4(), [(4, "# Fees\na b c d e f g h")])
    assert chunks[0].page == 4
    assert chunks[0].section == "Fees"
    assert chunks[0].ordinal == 0
    assert chunks[1].body.split()[:2] == chunks[0].body.split()[-2:]
    assert all(chunk.body_sha256 == hashlib.sha256(chunk.body.encode()).hexdigest() for chunk in chunks)


def test_snapshot_store_streams_and_uses_content_addressed_immutable_path(tmp_path: Path):
    async def run():
        store = LocalSnapshotStore(tmp_path, max_bytes=64)
        source = io.BytesIO(b"Verified lending text.\n")
        snapshot = await store.save(source, "policy.txt")
        assert source.tell() == 0
        assert Path(snapshot.path).read_bytes() == b"Verified lending text.\n"
        repeated = await store.save(io.BytesIO(b"Verified lending text.\n"), "another.txt")
        assert repeated.path == snapshot.path
        with pytest.raises(UploadRejected) as error:
            await store.save(io.BytesIO(b"x" * 65), "large.txt")
        assert error.value.code == "FILE_TOO_LARGE"
        with pytest.raises(UploadRejected):
            await store.save(io.BytesIO(b"<html>no</html>"), "fake.txt")

    asyncio.run(run())


def test_upload_use_case_binds_content_hash_metadata_and_operator(tmp_path: Path):
    async def run():
        repository = FakeRepository()
        store = LocalSnapshotStore(tmp_path)
        use_case = UploadKnowledgeDocument(repository, store)
        metadata = VerifiedDocumentMetadata("Verified", "reviewer", datetime.now(timezone.utc),
                                            source_url="https://example.org/source")
        result = await use_case.execute(UploadCommand(io.BytesIO(b"verified\n"), "guide.md", metadata,
                                                       "operator-1", "request-1"))
        assert result.document.ingestion_status is IngestionStatus.QUEUED
        assert repository.upload["operator_ref"] == "operator-1"
        assert repository.upload["idempotency_key"] == "request-1"
        assert len(repository.upload["request_fingerprint"]) == 64
        assert repository.upload["snapshot"].sha256 == hashlib.sha256(b"verified\n").hexdigest()

    asyncio.run(run())


def test_ingestion_publishes_only_complete_validated_vectors():
    async def run():
        repository = FakeRepository()
        use_case = ProcessKnowledgeDocument(repository, FakeExtractor(), KnowledgeChunker(WordTokenizer()),
                                            FakeEmbedder(), embedding_model="qwen/qwen3-embedding-8b")
        await use_case.execute(uuid4())
        _, chunks, vectors, metadata = repository.chunks
        assert chunks and len(vectors) == len(chunks)
        assert all(len(vector) == 1536 for vector in vectors)
        assert all(math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0) for vector in vectors)
        assert metadata["embedding_version"] == "mrl-prefix-1536-l2-v1"

    asyncio.run(run())


def test_ingestion_fails_closed_on_empty_extraction():
    class EmptyExtractor:
        def extract(self, _path, _media_type):
            return []

    async def run():
        repository = FakeRepository()
        use_case = ProcessKnowledgeDocument(repository, EmptyExtractor(), KnowledgeChunker(WordTokenizer()),
                                            FakeEmbedder(), embedding_model="qwen/qwen3-embedding-8b")
        with pytest.raises(RuntimeError, match="EXTRACTION_FAILED"):
            await use_case.execute(uuid4())
        assert repository.failure is not None
        assert repository.failure[1] == "EXTRACTION_FAILED"
        assert repository.chunks is None

    asyncio.run(run())


class FakeExtractor:
    def extract(self, _path, _media_type):
        return [(1, "# Eligibility\nLoan eligibility needs income documents.")]


class FakeEmbedder:
    async def embed_documents(self, texts):
        return [[1.0] + [0.0] * 1535 for _ in texts]
