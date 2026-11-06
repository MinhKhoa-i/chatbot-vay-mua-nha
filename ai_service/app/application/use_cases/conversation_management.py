from uuid import UUID

from app.domain.entities.conversation import Conversation
from app.domain.ports.conversation_repository import ConversationRepository

def _missing_slots(checkpoint: dict, profile_summary: dict) -> list[str]:
    pending_tasks = checkpoint.get("pending_tasks")
    if isinstance(pending_tasks, list) and pending_tasks and isinstance(pending_tasks[0], dict):
        required = pending_tasks[0].get("required_slots")
        if isinstance(required, list):
            return [name for name in required if profile_summary.get(name, {}).get("value") is None]
    return []


class ConversationNotFound(LookupError):
    pass


class ConversationStateUnavailable(RuntimeError):
    pass


class ConversationManagement:
    """Use cases for creating, reading, listing and deleting conversations."""

    def __init__(self, repository: ConversationRepository) -> None:
        self._repository = repository

    async def create(self) -> Conversation:
        return await self._repository.create()

    async def get(self, conversation_id: UUID) -> Conversation:
        conversation = await self._repository.get(conversation_id)
        if conversation is None:
            raise ConversationNotFound from None
        return conversation

    async def get_detail(self, conversation_id: UUID) -> tuple[Conversation, list[str]]:
        conversation = await self.get(conversation_id)
        return conversation, _missing_slots(conversation.checkpoint, conversation.profile_summary)

    async def list_messages(self, conversation_id: UUID, *, before: int | None, limit: int):
        result = await self._repository.list_messages(conversation_id, before=before, limit=limit)
        if result is None:
            raise ConversationNotFound from None
        return result

    async def delete(self, conversation_id: UUID) -> None:
        deleted = await self._repository.delete(conversation_id)
        if not deleted:
            raise ConversationNotFound from None
