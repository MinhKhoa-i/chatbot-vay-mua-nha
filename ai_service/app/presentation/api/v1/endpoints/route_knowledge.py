import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Response, UploadFile, status
from pydantic import ValidationError

from app.application.use_cases.upload_knowledge_document import (
    GetKnowledgeDocument,
    SetKnowledgeDocumentActive,
    UploadCommand,
    UploadKnowledgeDocument,
)
from app.infrastructure.knowledge.local_snapshot_store import UploadRejected
from app.infrastructure.knowledge.postgres_knowledge_repository import DocumentConflict
from app.presentation.api.knowledge_schemas import (
    KnowledgeDocumentResponse,
    UpdateKnowledgeActivation,
    UploadMetadata,
)
from app.presentation.api.knowledge_dependencies import (
    get_document_activation_updater,
    get_document_reader,
    get_upload_use_case,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge/documents", tags=["knowledge"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=KnowledgeDocumentResponse)
async def upload_document(
    response: Response,
    file: UploadFile = File(...),
    metadata: str = Form(...),
    use_case: UploadKnowledgeDocument = Depends(get_upload_use_case),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    # from app.core.config import get_settings
    # settings = get_settings()
    # print(settings)
    try:
        parsed_metadata = UploadMetadata.parse_json(metadata)
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail="INVALID_METADATA") from exc
    if idempotency_key is not None and (not idempotency_key.strip() or len(idempotency_key) > 200):
        raise HTTPException(status_code=422, detail="INVALID_IDEMPOTENCY_KEY")
    try:
        result = await use_case.execute(
            UploadCommand(
                file=file,
                filename=file.filename or "",
                metadata=parsed_metadata.to_domain(),
                operator_ref="internal",
                idempotency_key=idempotency_key,
            )
        )
    except UploadRejected as exc:
        code = exc.code
        http_status = 413 if code == "FILE_TOO_LARGE" else 415 if code == "UNSUPPORTED_FILE_TYPE" else 422
        raise HTTPException(status_code=http_status, detail=code) from exc
    except DocumentConflict as exc:
        raise HTTPException(status_code=409, detail=exc.code) from exc
    except Exception as exc:
        logger.exception("Knowledge upload failed")
        raise HTTPException(status_code=503, detail="KNOWLEDGE_STORAGE_UNAVAILABLE") from exc
    finally:
        await file.close()
    response.status_code = status.HTTP_200_OK if not result.created else status.HTTP_202_ACCEPTED
    return KnowledgeDocumentResponse.from_domain(result.document)


@router.patch("/{document_id}/activation", response_model=KnowledgeDocumentResponse)
async def update_document_activation(
    document_id: UUID,
    payload: UpdateKnowledgeActivation,
    use_case: Annotated[SetKnowledgeDocumentActive, Depends(get_document_activation_updater)],
):
    document = await use_case.execute(document_id, payload.is_active)
    if document is None:
        raise HTTPException(status_code=404, detail="DOCUMENT_NOT_FOUND")
    return KnowledgeDocumentResponse.from_domain(document)


@router.get("/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_document_status(
    document_id: UUID,
    use_case: Annotated[GetKnowledgeDocument, Depends(get_document_reader)],
):
    document = await use_case.execute(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="DOCUMENT_NOT_FOUND")
    return KnowledgeDocumentResponse.from_domain(document)
