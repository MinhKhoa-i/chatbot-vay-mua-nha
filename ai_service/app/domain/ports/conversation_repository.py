from typing import Protocol
from uuid import UUID

from app.domain.entities.conversation import Conversation, ConversationMessage


class ConversationRepository(Protocol):
    async def create(self) -> Conversation: ...

    async def get(self, conversation_id: UUID) -> Conversation | None: ...

    async def list_messages(
        self, conversation_id: UUID, *, before: int | None, limit: int
    ) -> tuple[list[ConversationMessage], int | None] | None: ...

    async def delete(self, conversation_id: UUID) -> bool: ...
