import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.application.use_cases.stream_chat import StreamChatUseCase
from app.core.config import get_settings
from app.infrastructure.llm.openai_chat_adapter import ChatProviderUnavailable
from app.presentation.api.chat_dependencies import get_stream_chat_use_case
from app.presentation.api.schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["chat"])


def _sse(event: str, payload: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post(
    "/{conversation_id}/messages",
    status_code=status.HTTP_200_OK,
    responses={200: {"content": {"text/event-stream": {}}}, 503: {"description": "Chat provider unavailable"}},
)
async def stream_message(
    conversation_id: UUID,
    request: ChatRequest,
    use_case: StreamChatUseCase = Depends(get_stream_chat_use_case),
) -> StreamingResponse:
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="INVALID_INPUT")
    settings = get_settings()
    encoded_request = request.model_dump_json().encode("utf-8")
    if len(encoded_request) > 20 * 1024:
        raise HTTPException(status_code=422, detail="INVALID_INPUT")
    if not settings.llm_base_url or not settings.llm_api_key:
        raise HTTPException(status_code=503, detail="MODEL_UNAVAILABLE")

    async def events() -> AsyncIterator[str]:
        try:
            async for fragment in use_case.execute(conversation_id, request.message):
                yield _sse("delta", {"text": fragment})
            yield _sse("done", {"status": "completed"})
        except ChatProviderUnavailable:
            logger.warning("Chat provider unavailable while streaming")
            yield _sse("error", {"code": "MODEL_UNAVAILABLE", "message": "Dịch vụ tư vấn hiện tạm thời không khả dụng."})
        except Exception:
            logger.exception("Unexpected error while streaming chat")
            yield _sse("error", {"code": "INTERNAL_ERROR", "message": "Đã xảy ra lỗi khi xử lý yêu cầu."})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Accel-Buffering": "no",
        },
    )
