from datetime import date, datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ConversationModel(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        # Active/closed state has a current encrypted checkpoint; deleted rows are tombstones.
        CheckConstraint("status IN ('active','closed','deleted')"),
        CheckConstraint(
            "(status IN ('active','closed') AND checkpoint_ciphertext IS NOT NULL AND deleted_at IS NULL) "
            "OR (status='deleted' AND checkpoint_ciphertext IS NULL AND deleted_at IS NOT NULL "
            "AND active_request_id IS NULL)"
        ),
        CheckConstraint("expires_at > last_active_at"),
        Index("ix_conversations_expiry", "expires_at", postgresql_where=text("status <> 'deleted'")),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'"))
    checkpoint_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    active_request_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConversationProfileModel(Base):
    __tablename__ = "conversation_profiles"

    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    slots_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ConversationMessageModel(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "seq"),
        CheckConstraint("role IN ('user','assistant','system')"),
        CheckConstraint("seq > 0"),
        Index("ix_messages_conversation_seq", "conversation_id", text("seq DESC")),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    seq: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MessageRequestModel(Base):
    __tablename__ = "message_requests"
    __table_args__ = (
        UniqueConstraint("conversation_id", "client_request_id"),
        CheckConstraint(
            "operation IN ('send_message','patch_profile','confirm_profile','calculate_loan','recommend_banks')"
        ),
        CheckConstraint("status IN ('processing','completed','failed')"),
        CheckConstraint("snapshot_version >= 0"),
        CheckConstraint("attempts BETWEEN 1 AND max_attempts"),
        CheckConstraint(
            "status<>'completed' OR (response_ciphertext IS NOT NULL AND response_status BETWEEN 200 AND 299 "
            "AND error_code IS NULL AND retryable=false)"
        ),
        CheckConstraint(
            "status<>'failed' OR (error_code IS NOT NULL AND response_ciphertext IS NOT NULL "
            "AND response_status BETWEEN 400 AND 599)"
        ),
        CheckConstraint("retryable=false OR (status='failed' AND attempts < max_attempts)"),
        CheckConstraint(
            "(status='processing' AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL) "
            "OR (status<>'processing' AND lease_token IS NULL AND lease_expires_at IS NULL)"
        ),
        Index(
            "uq_requests_one_processing", "conversation_id", unique=True,
            postgresql_where=text("status='processing'"),
        ),
        Index(
            "ix_requests_lease", "lease_expires_at", postgresql_where=text("status='processing'")
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    client_request_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    operation: Mapped[str] = mapped_column(String(40), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    lease_token: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    retryable: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    response_status: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class KnowledgeDocumentModel(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint("logical_document_id", "version_no"),
        UniqueConstraint("logical_document_id", "content_sha256"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    logical_document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    bank_code: Mapped[str | None] = mapped_column(String(50))
    product_type: Mapped[str | None] = mapped_column(String(100))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_path: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    last_updated: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    uploaded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingestion_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))


class KnowledgeChunkModel(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("document_id", "ordinal"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(200), nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(100), nullable=False)
    textsearch: Mapped[str] = mapped_column(TSVECTOR, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    body_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class KnowledgeUploadRequestModel(Base):
    __tablename__ = "knowledge_upload_requests"

    operator_ref: Mapped[str] = mapped_column(String(200), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
