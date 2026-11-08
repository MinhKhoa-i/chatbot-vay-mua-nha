from typing import Protocol

from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.errors import ChatError


class IntentClassificationError(ChatError):
    """Classification failed; do not bypass retrieval with an unverified intent."""

    def __init__(
        self, code: str = "CLASSIFICATION_UNAVAILABLE", *, retryable: bool = True,
    ) -> None:
        super().__init__(code, stage="classification", retryable=retryable)


class ChatIntentClassifier(Protocol):
    async def classify(
        self, text: str, *, history: tuple[tuple[str, str], ...] = (),
    ) -> ChatIntent:
        """Classify the current message using committed conversational context."""
        ...
