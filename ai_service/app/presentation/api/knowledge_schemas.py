import json
from datetime import date, datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.domain.entities.knowledge_document import IngestionStatus, StoredDocument, VerifiedDocumentMetadata


class UploadMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    verified: bool
    reviewed_by: str = Field(min_length=1, max_length=200)
    reviewed_at: datetime
    source_url: HttpUrl | None = None
    bank_code: str | None = Field(default=None, max_length=50)
    product_type: str | None = Field(default=None, max_length=100)
    effective_from: date | None = None
    effective_to: date | None = None
    last_updated: date | None = None
    retrieved_at: datetime | None = None
    logical_document_id: UUID | None = None

    @field_validator("source_url")
    @classmethod
    def validate_public_http_url(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is not None and value.scheme not in {"http", "https"}:
            raise ValueError("source_url must use HTTP or HTTPS")
        if value is not None and (value.username or value.password):
            raise ValueError("source_url must not contain credentials")
        return value

    @model_validator(mode="after")
    def validate_verified_metadata(self):
        if self.verified is not True:
            raise ValueError("verified must be true")
        if self.effective_from and self.effective_to and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be later than effective_from")
        if self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None:
            raise ValueError("reviewed_at must be timezone-aware")
        if self.retrieved_at and (self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None):
            raise ValueError("retrieved_at must be timezone-aware")
        return self

    @classmethod
    def parse_json(cls, value: str) -> "UploadMetadata":
        return cls.model_validate(json.loads(value))

    def to_domain(self) -> VerifiedDocumentMetadata:
        return VerifiedDocumentMetadata(
            title=self.title.strip(), reviewed_by=self.reviewed_by.strip(),
            reviewed_at=self.reviewed_at.astimezone(timezone.utc),
            source_url=str(self.source_url) if self.source_url else None,
            bank_code=self.bank_code, product_type=self.product_type,
            effective_from=self.effective_from, effective_to=self.effective_to,
            last_updated=self.last_updated,
            retrieved_at=self.retrieved_at.astimezone(timezone.utc) if self.retrieved_at else None,
            logical_document_id=self.logical_document_id,
        )


class KnowledgeDocumentResponse(BaseModel):
    document_id: UUID
    logical_document_id: UUID
    version_no: int
    title: str
    source_url: str | None
    review_status: str
    ingestion_status: IngestionStatus
    error_code: str | None = None

    @classmethod
    def from_domain(cls, document: StoredDocument) -> "KnowledgeDocumentResponse":
        return cls(
            document_id=document.id, logical_document_id=document.logical_document_id,
            version_no=document.version_no, title=document.title, source_url=document.source_url,
            review_status=document.review_status, ingestion_status=document.ingestion_status,
            error_code=document.error_code,
        )
