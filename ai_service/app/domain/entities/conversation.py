from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

ConversationStatus = Literal["active", "closed"]
MessageRole = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class Conversation:
    id: UUID
    status: ConversationStatus
    version: int
    profile_revision: int
    checkpoint: dict
    profile_summary: dict
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    id: UUID
    role: MessageRole
    content: str
    seq: int
    created_at: datetime
