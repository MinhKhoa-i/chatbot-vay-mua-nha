from collections.abc import AsyncIterator
from uuid import UUID

from app.domain.ports.chat_completion import ChatCompletionPort


class StreamChatUseCase:
    """Application boundary for streaming one chat turn."""

    def __init__(self, completion: ChatCompletionPort) -> None:
        self._completion = completion

    async def execute(self, conversation_id: UUID, text: str) -> AsyncIterator[str]:
        # Conversation history/state is not yet persisted by this repository scaffold.
        # Do not send the conversation ID to the model/provider.
        async for fragment in self._completion.stream_reply(text):
            yield fragment
