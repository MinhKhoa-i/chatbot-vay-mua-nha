from functools import lru_cache
from pathlib import Path
from typing import Annotated


from app.application.services.knowledge_chunker import KnowledgeChunker
from app.application.use_cases.process_knowledge_document import ProcessKnowledgeDocument
from app.application.use_cases.upload_knowledge_document import (
    GetKnowledgeDocument,
    SetKnowledgeDocumentActive,
    UploadKnowledgeDocument,
)
from app.core.config import Settings
from app.infrastructure.db.session import get_async_session_factory
from app.infrastructure.knowledge.document_extractor import LocalDocumentExtractor
from app.infrastructure.knowledge.local_snapshot_store import LocalSnapshotStore
from app.infrastructure.knowledge.postgres_knowledge_repository import PostgresKnowledgeRepository
from app.infrastructure.knowledge.qwen_embedding_adapter import QwenEmbeddingAdapter
from app.infrastructure.knowledge.tiktoken_tokenizer import TiktokenTokenizer


@lru_cache
def get_snapshot_store() -> LocalSnapshotStore:
    settings = Settings()
    return LocalSnapshotStore(Path(settings.knowledge_snapshot_dir))


def get_knowledge_repository() -> PostgresKnowledgeRepository:
    return PostgresKnowledgeRepository(get_async_session_factory())


def get_upload_use_case() -> UploadKnowledgeDocument:
    return UploadKnowledgeDocument(get_knowledge_repository(), get_snapshot_store())


def get_document_reader() -> GetKnowledgeDocument:
    return GetKnowledgeDocument(get_knowledge_repository())


def get_document_activation_updater() -> SetKnowledgeDocumentActive:
    return SetKnowledgeDocumentActive(get_knowledge_repository())


def get_document_processor() -> ProcessKnowledgeDocument:
    settings = Settings()
    tokenizer = TiktokenTokenizer()
    return ProcessKnowledgeDocument(
        get_knowledge_repository(),
        LocalDocumentExtractor(snapshot_root=Path(settings.knowledge_snapshot_dir)),
        KnowledgeChunker(tokenizer),
        QwenEmbeddingAdapter(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            source_dimensions=4096,
        ),
        embedding_model=settings.embedding_model,
    )

