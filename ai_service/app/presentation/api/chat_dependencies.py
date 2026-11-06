from functools import lru_cache

from app.application.use_cases.stream_chat import StreamChatUseCase
from app.core.config import get_settings
from app.infrastructure.llm.openai_chat_adapter import OpenAIChatAdapter


@lru_cache
def get_stream_chat_use_case() -> StreamChatUseCase:
    settings = get_settings()
    return StreamChatUseCase(
        OpenAIChatAdapter(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    )
