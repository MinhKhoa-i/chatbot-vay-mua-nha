from collections.abc import AsyncIterator
from typing import Protocol


class ChatCompletionPort(Protocol):
    def stream_reply(self, text: str) -> AsyncIterator[str]:
        """Yield generated text fragments for one user message."""
        ...
