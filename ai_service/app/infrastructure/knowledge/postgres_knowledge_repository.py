import json
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.knowledge_document import IngestionStatus, StoredDocument, VerifiedDocumentMetadata
from app.domain.entities.knowledge_evidence import KnowledgeEvidence, KnowledgeSearchQuery
from app.domain.ports.knowledge_ingestion import IngestionJob, KnowledgeChunk, Snapshot, UploadResult


class DocumentConflict(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PostgresKnowledgeRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def register_upload(self, *, operator_ref: str, idempotency_key: str | None,
                              request_fingerprint: str, metadata: VerifiedDocumentMetadata,
                              snapshot: Snapshot) -> UploadResult:
        try:
            return await self._register_upload_transaction(
                operator_ref=operator_ref, idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint, metadata=metadata, snapshot=snapshot,
            )
        except IntegrityError as exc:
            if idempotency_key:
                async with self._sessions() as session:
                    row = (await session.execute(text("""
                        SELECT r.request_fingerprint, d.* FROM knowledge_upload_requests r
                        JOIN knowledge_documents d ON d.id = r.document_id
                        WHERE r.operator_ref = :operator_ref AND r.idempotency_key = :key
                    """), {"operator_ref": operator_ref, "key": idempotency_key})).mappings().first()
                    if row:
                        if row["request_fingerprint"] != request_fingerprint:
                            raise DocumentConflict("IDEMPOTENCY_KEY_REUSED") from exc
                        return UploadResult(self._to_document(row), False)
            raise DocumentConflict("DOCUMENT_METADATA_CONFLICT") from exc

    async def _register_upload_transaction(self, *, operator_ref: str, idempotency_key: str | None,
                                           request_fingerprint: str, metadata: VerifiedDocumentMetadata,
                                           snapshot: Snapshot) -> UploadResult:
        async with self._sessions() as session, session.begin():
            if idempotency_key:
                existing = (await session.execute(text("""
                    SELECT r.request_fingerprint, d.* FROM knowledge_upload_requests r
                    JOIN knowledge_documents d ON d.id = r.document_id
                    WHERE r.operator_ref = :operator_ref AND r.idempotency_key = :key
                    FOR UPDATE OF r
                """), {"operator_ref": operator_ref, "key": idempotency_key})).mappings().first()
                if existing:
                    if existing["request_fingerprint"] != request_fingerprint:
                        raise DocumentConflict("IDEMPOTENCY_KEY_REUSED")
                    return UploadResult(self._to_document(existing), False)

            logical_id = metadata.logical_document_id or uuid4()
            # Serialize all writes for this logical document before duplicate/version checks.
            await session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:logical_id, 0))"),
                                  {"logical_id": str(logical_id)})
            duplicate = (await session.execute(text("""
                SELECT * FROM knowledge_documents
                WHERE logical_document_id = :logical_id AND content_sha256 = :sha FOR UPDATE
            """), {"logical_id": logical_id, "sha": snapshot.sha256})).mappings().first()
            if duplicate:
                if not self._metadata_matches(duplicate, metadata):
                    raise DocumentConflict("DOCUMENT_METADATA_CONFLICT")
                document = self._to_document(duplicate)
                if idempotency_key:
                    await self._insert_upload_request(session, operator_ref, idempotency_key,
                                                      request_fingerprint, document.id)
                return UploadResult(document, False)

            next_version = (await session.execute(text("""
                SELECT COALESCE(MAX(version_no), 0) + 1 FROM knowledge_documents
                WHERE logical_document_id = :logical_id
            """), {"logical_id": logical_id})).scalar_one()
            document_id = uuid4()
            row = (await session.execute(text("""
                INSERT INTO knowledge_documents (
                    id, logical_document_id, source_url, title, bank_code, product_type,
                    original_filename, media_type, size_bytes, content_sha256, snapshot_path,
                    effective_from, effective_to, last_updated, retrieved_at, uploaded_at,
                    uploaded_by, review_status, reviewed_by, reviewed_at, ingestion_status, version_no
                ) VALUES (
                    :id, :logical_id, :source_url, :title, :bank_code, :product_type,
                    :filename, :media_type, :size, :sha, :snapshot_path,
                    :effective_from, :effective_to, :last_updated, :retrieved_at, now(),
                    :uploaded_by, 'approved', :reviewed_by, :reviewed_at, 'queued', :version_no
                ) RETURNING *
            """), {
                "id": document_id, "logical_id": logical_id, "source_url": metadata.source_url,
                "title": metadata.title, "bank_code": metadata.bank_code, "product_type": metadata.product_type,
                "filename": snapshot.original_filename, "media_type": snapshot.media_type,
                "size": snapshot.size_bytes, "sha": snapshot.sha256, "snapshot_path": snapshot.path,
                "effective_from": metadata.effective_from, "effective_to": metadata.effective_to,
                "last_updated": metadata.last_updated, "retrieved_at": metadata.retrieved_at,
                "uploaded_by": operator_ref, "reviewed_by": metadata.reviewed_by,
                "reviewed_at": metadata.reviewed_at, "version_no": next_version,
            })).mappings().one()
            document = self._to_document(row)
            await session.execute(text("""
                INSERT INTO source_reviews (id, document_id, reviewer_ref, decision, reviewed_at)
                VALUES (:id, :document_id, :reviewer, 'approved', :reviewed_at)
            """), {"id": uuid4(), "document_id": document_id, "reviewer": metadata.reviewed_by,
                  "reviewed_at": metadata.reviewed_at})
            await session.execute(text("""
                INSERT INTO background_jobs (id, kind, payload, status, run_after, attempts, max_attempts, idempotency_key)
                VALUES (:id, 'knowledge_ingestion', CAST(:payload AS jsonb), 'pending', now(), 0, 5, :job_key)
                ON CONFLICT (idempotency_key) DO NOTHING
            """), {"id": uuid4(), "payload": json.dumps({"document_id": str(document_id)}),
                  "job_key": f"knowledge-ingestion:{document_id}"})
            if idempotency_key:
                await self._insert_upload_request(session, operator_ref, idempotency_key,
                                                  request_fingerprint, document_id)
            return UploadResult(document, True)

    @staticmethod
    async def _insert_upload_request(session, operator_ref: str, key: str, fingerprint: str,
                                    document_id: UUID) -> None:
        await session.execute(text("""
            INSERT INTO knowledge_upload_requests (operator_ref, idempotency_key, request_fingerprint,
                                                   document_id, created_at)
            VALUES (:operator_ref, :key, :fingerprint, :document_id, now())
            ON CONFLICT (operator_ref, idempotency_key) DO NOTHING
        """), {"operator_ref": operator_ref, "key": key, "fingerprint": fingerprint,
              "document_id": document_id})

    async def get_document(self, document_id: UUID) -> StoredDocument | None:
        async with self._sessions() as session:
            row = (await session.execute(text("SELECT * FROM knowledge_documents WHERE id = :id"),
                                         {"id": document_id})).mappings().first()
            return self._to_document(row) if row else None

    async def set_document_active(self, document_id: UUID, is_active: bool) -> StoredDocument | None:
        async with self._sessions() as session, session.begin():
            row = (await session.execute(text("""
                SELECT * FROM knowledge_documents WHERE id = :id FOR UPDATE
            """), {"id": document_id})).mappings().first()
            if row is None:
                return None
            if row["is_active"] is is_active:
                return self._to_document(row)
            updated = (await session.execute(text("""
                UPDATE knowledge_documents
                SET is_active = :is_active
                WHERE id = :id
                RETURNING *
            """), {"id": document_id, "is_active": is_active})).mappings().one()
            return self._to_document(updated)

    async def claim_ingestion(self, document_id: UUID) -> IngestionJob | None:
        async with self._sessions() as session, session.begin():
            row = (await session.execute(text("""
                UPDATE knowledge_documents SET ingestion_status = 'processing', error_code = NULL
                WHERE id = :id AND ingestion_status IN ('queued', 'failed')
                RETURNING id, snapshot_path, media_type, content_sha256, effective_from, effective_to
            """), {"id": document_id})).mappings().first()
            if row is None:
                return None
            run_id = uuid4()
            await session.execute(text("""
                INSERT INTO ingestion_runs (id, document_id, status, sha256, started_at)
                VALUES (:id, :document_id, 'processing', :sha, now())
            """), {"id": run_id, "document_id": document_id, "sha": row["content_sha256"]})
            return IngestionJob(run_id, document_id, row["snapshot_path"], row["media_type"],
                                row["content_sha256"], row["effective_from"], row["effective_to"])

    async def publish_chunks(self, job: IngestionJob, chunks: list[KnowledgeChunk],
                             embeddings: list[list[float]], *, embedding_model: str,
                             embedding_version: str, effective_from: date | None,
                             effective_to: date | None) -> None:
        async with self._sessions() as session, session.begin():
            current = (await session.execute(text("""
                SELECT id FROM knowledge_documents WHERE id = :id AND ingestion_status = 'processing'
                  AND content_sha256 = :sha FOR UPDATE
            """), {"id": job.document_id, "sha": job.expected_sha256})).scalar_one_or_none()
            if current is None:
                raise RuntimeError("ingestion claim lost")
            await session.execute(text("DELETE FROM knowledge_chunks WHERE document_id = :id"),
                                  {"id": job.document_id})
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                vector_literal = "[" + ",".join(format(value, ".9g") for value in embedding) + "]"
                await session.execute(text("""
                    INSERT INTO knowledge_chunks
                        (id, document_id, ordinal, body, embedding, embedding_model, embedding_version,
                         textsearch, metadata, body_sha256)
                    VALUES (:id, :document_id, :ordinal, :body, CAST(:embedding AS vector), :model, :version,
                            to_tsvector('simple', :body), CAST(:metadata AS jsonb), :sha)
                """), {"id": uuid4(), "document_id": job.document_id, "ordinal": chunk.ordinal,
                      "body": chunk.body, "embedding": vector_literal, "model": embedding_model,
                      "version": embedding_version,
                      "metadata": json.dumps({
                          "page": chunk.page, "section": chunk.section,
                          "effective_from": chunk.effective_from, "effective_to": chunk.effective_to,
                      }),
                      "sha": chunk.body_sha256})
            await session.execute(text("""
                UPDATE knowledge_documents SET ingestion_status = 'published', error_code = NULL
                WHERE id = :id AND ingestion_status = 'processing'
            """), {"id": job.document_id})
            await session.execute(text("""
                UPDATE ingestion_runs SET status = 'published', finished_at = now()
                WHERE id = :id AND status = 'processing'
            """), {"id": job.id})

    async def search_approved(self, query: KnowledgeSearchQuery) -> tuple[KnowledgeEvidence, ...]:
        if not query.text.strip() or not query.embedding or query.limit < 1:
            return ()
        vector_literal = "[" + ",".join(format(float(value), ".9g") for value in query.embedding) + "]"
        async with self._sessions() as session:
            rows = (await session.execute(text("""
                WITH candidates AS (
                    SELECT c.id AS chunk_id, d.id AS document_id, d.title, d.source_url,
                           d.bank_code, d.product_type, d.effective_from, d.effective_to,
                           c.body,
                           (1 - (c.embedding <=> CAST(:embedding AS vector))) AS vector_score,
                           ts_rank_cd(c.textsearch, plainto_tsquery('simple', :query_text)) AS text_score
                    FROM knowledge_chunks c
                    JOIN knowledge_documents d ON d.id = c.document_id
                    WHERE d.review_status = 'approved'
                      AND d.ingestion_status = 'published'
                      AND d.is_active = true
                      AND (d.effective_from IS NULL OR d.effective_from <= CURRENT_DATE)
                      AND (d.effective_to IS NULL OR d.effective_to > CURRENT_DATE)
                )
                SELECT *, GREATEST(vector_score, LEAST(text_score, 1.0)) AS score
                FROM candidates
                WHERE vector_score > 0 OR text_score > 0
                ORDER BY score DESC, vector_score DESC, document_id, chunk_id
                LIMIT :limit
            """), {
                "embedding": vector_literal,
                "query_text": query.text[:4000],
                "limit": query.limit,
            })).mappings().all()
        return tuple(
            KnowledgeEvidence(
                chunk_id=row["chunk_id"], document_id=row["document_id"],
                title=row["title"], source_url=row["source_url"], body=row["body"],
                score=float(row["score"]), bank_code=row["bank_code"], product_type=row["product_type"],
                effective_from=row["effective_from"], effective_to=row["effective_to"],
            )
            for row in rows if float(row["score"]) >= query.min_score
        )

    async def fail_ingestion(self, job: IngestionJob, error_code: str) -> None:
        async with self._sessions() as session, session.begin():
            await session.execute(text("""
                UPDATE knowledge_documents SET ingestion_status = 'failed', error_code = :error
                WHERE id = :id AND ingestion_status = 'processing' AND content_sha256 = :sha
            """), {"id": job.document_id, "sha": job.expected_sha256, "error": error_code})
            await session.execute(text("""
                UPDATE ingestion_runs SET status = 'failed', finished_at = now(), error_code = :error
                WHERE id = :id AND status = 'processing'
            """), {"id": job.id, "error": error_code})

    @staticmethod
    def _metadata_matches(row, metadata: VerifiedDocumentMetadata) -> bool:
        return (row["title"] == metadata.title and row["source_url"] == metadata.source_url
                and row["bank_code"] == metadata.bank_code and row["product_type"] == metadata.product_type
                and row["effective_from"] == metadata.effective_from
                and row["effective_to"] == metadata.effective_to
                and row["last_updated"] == metadata.last_updated
                and row["retrieved_at"] == metadata.retrieved_at
                and row["reviewed_by"] == metadata.reviewed_by
                and row["reviewed_at"] == metadata.reviewed_at)

    @staticmethod
    def _to_document(row) -> StoredDocument:
        return StoredDocument(
            id=row["id"], logical_document_id=row["logical_document_id"], version_no=row["version_no"],
            title=row["title"], source_url=row["source_url"], content_sha256=row["content_sha256"],
            snapshot_path=row["snapshot_path"], media_type=row["media_type"], size_bytes=row["size_bytes"],
            ingestion_status=IngestionStatus(row["ingestion_status"]), review_status=row["review_status"],
            is_active=row["is_active"], error_code=row.get("error_code"),
        )
