import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.application.use_cases.conversation_management import (
    ConversationManagement,
    ConversationNotFound,
)
from app.infrastructure.security.payload_cipher import PayloadCipherError
from app.presentation.api.conversation_dependencies import get_conversation_management
from app.presentation.api.conversation_schemas import (
    ConversationDetailResponse,
    ConversationMessageResponse,
    ConversationMessagesResponse,
    ConversationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["conversations"])


def _state_unavailable() -> HTTPException:
    logger.error("Conversation state failed integrity validation")
    return HTTPException(status_code=503, detail="STATE_UNAVAILABLE")


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ConversationResponse)
async def create_conversation(
    management: Annotated[ConversationManagement, Depends(get_conversation_management)],
) -> ConversationResponse:
    try:
        conversation = await management.create()
    except PayloadCipherError as exc:
        raise _state_unavailable() from exc
    except Exception as exc:
        logger.error("Could not create conversation; state service unavailable")
        raise HTTPException(status_code=503, detail="STATE_UNAVAILABLE") from exc
    return ConversationResponse(
        conversation_id=conversation.id,
        conversation_version=conversation.version,
        profile_revision=conversation.profile_revision,
        created_at=conversation.created_at,
        expires_at=conversation.expires_at,
        status=conversation.status,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    management: Annotated[ConversationManagement, Depends(get_conversation_management)],
) -> ConversationDetailResponse:
    try:
        conversation, missing_slots = await management.get_detail(conversation_id)
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail="CONVERSATION_NOT_FOUND") from exc
    except PayloadCipherError as exc:
        raise _state_unavailable() from exc
    except Exception as exc:
        logger.error("Could not read conversation state; state service unavailable")
        raise HTTPException(status_code=503, detail="STATE_UNAVAILABLE") from exc
    return ConversationDetailResponse(
        conversation_id=conversation.id,
        conversation_version=conversation.version,
        profile_revision=conversation.profile_revision,
        created_at=conversation.created_at,
        expires_at=conversation.expires_at,
        status=conversation.status,
        state=str(conversation.checkpoint.get("current_stage", "NEW")),
        profile_summary=conversation.profile_summary,
        missing_slots=missing_slots,
    )


@router.get("/{conversation_id}/messages", response_model=ConversationMessagesResponse)
async def get_messages(
    conversation_id: UUID,
    management: Annotated[ConversationManagement, Depends(get_conversation_management)],
    limit: int = Query(default=50, ge=1, le=100),
    before: int | None = Query(default=None, ge=1),
) -> ConversationMessagesResponse:
    try:
        result = await management.list_messages(conversation_id, before=before, limit=limit)
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail="CONVERSATION_NOT_FOUND") from exc
    except PayloadCipherError as exc:
        raise _state_unavailable() from exc
    except Exception as exc:
        logger.error("Could not read conversation messages; state service unavailable")
        raise HTTPException(status_code=503, detail="STATE_UNAVAILABLE") from exc
    items, next_cursor = result
    return ConversationMessagesResponse(
        items=[
            ConversationMessageResponse(
                message_id=item.id,
                role=item.role,
                content=item.content,
                seq=item.seq,
                created_at=item.created_at,
            )
            for item in items
        ],
        next_cursor=next_cursor,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    management: Annotated[ConversationManagement, Depends(get_conversation_management)],
) -> Response:
    try:
        await management.delete(conversation_id)
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail="CONVERSATION_NOT_FOUND") from exc
    except Exception as exc:
        logger.error("Could not delete conversation; state service unavailable")
        raise HTTPException(status_code=503, detail="STATE_UNAVAILABLE") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
