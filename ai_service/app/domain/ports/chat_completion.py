from collections.abc import AsyncIterator
from typing import Protocol

from app.domain.errors import ChatError


class ChatProviderUnavailable(ChatError):
    """Raised by the provider adapter with safe failure metadata."""

    def __init__(
        self, message: str = "chat provider unavailable", *,
        code: str = "MODEL_UNAVAILABLE", retryable: bool = True,
    ) -> None:
        super().__init__(code, stage="model", retryable=retryable)
        # Preserve a safe code as the exception message; details remain in __cause__.


class ChatCompletionPort(Protocol):
    def stream_reply(
        self,
        text: str,
        *,
        history: tuple[tuple[str, str], ...] = (),
        guidance: str = "",
        knowledge_context: str = "",
    ) -> AsyncIterator[str]:
        """Yield generated fragments using prior turns and trusted application context."""
        ...
