import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.application.use_cases.stream_chat import StreamChatUseCase
from app.domain.errors import ChatError
from app.domain.entities.chat_request import ChatRequest as ChatTurnRequest, ChatTurnError
from app.presentation.api.chat_dependencies import get_stream_chat_use_case
from app.presentation.api.schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["chat"])


def _sse(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post(
    "/{conversation_id}/messages",
    status_code=status.HTTP_200_OK,
    responses={200: {"content": {"text/event-stream": {}}}, 503: {"description": "Chat provider unavailable"}},
)
async def stream_message(
    conversation_id: UUID,
    request: ChatRequest,
    http_request: Request,
    use_case: StreamChatUseCase = Depends(get_stream_chat_use_case),
) -> StreamingResponse:
    if use_case is None:
        raise HTTPException(status_code=503, detail="STATE_UNAVAILABLE")
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="INVALID_INPUT")
    encoded_request = request.model_dump_json().encode("utf-8")
    if len(encoded_request) > 20 * 1024:
        raise HTTPException(status_code=422, detail="INVALID_INPUT")
    content_length = http_request.headers.get("content-length")
    if content_length is not None:
        try:
            too_large = int(content_length) > 20 * 1024
        except ValueError:
            raise HTTPException(status_code=400, detail="INVALID_CONTENT_LENGTH") from None
        if too_large:
            raise HTTPException(status_code=413, detail="REQUEST_TOO_LARGE")
    async def events() -> AsyncIterator[str]:
        try:
            turn_request = ChatTurnRequest(
                conversation_id=conversation_id,
                client_request_id=request.client_request_id,
                text=request.text,
                expected_version=request.expected_version,
            )
            async for event in use_case.execute(turn_request):
                if event.event == "replay":
                    # A completed retry returns the original durable result without invoking the provider.
                    yield _sse("done", event.data)
                elif event.event == "delta":
                    yield _sse("delta", event.data)
                else:
                    yield _sse(event.event, event.data)
        except ChatTurnError as exc:
            logger.info("Chat turn rejected with code %s", exc.code)
            yield _sse("error", {"code": exc.code, "retryable": exc.retryable})
        except ChatError as exc:
            logger.exception("Chat failure (code=%s, stage=%s)", exc.code, exc.stage)
            yield _sse("error", exc.public_payload())
        except Exception:
            logger.exception("Unexpected error while processing chat turn")
            yield _sse("error", {"code": "INTERNAL_ERROR", "retryable": False})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Accel-Buffering": "no",
        },
    )
