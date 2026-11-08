from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationResponse(BaseModel):
    conversation_id: UUID
    conversation_version: int
    profile_revision: int
    created_at: datetime
    expires_at: datetime
    status: Literal["active", "closed"]


class ConversationDetailResponse(ConversationResponse):
    state: str
    profile_summary: dict = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)


class ConversationMessageResponse(BaseModel):
    message_id: UUID
    role: Literal["user", "assistant"]
    content: str
    seq: int
    created_at: datetime


class ConversationMessagesResponse(BaseModel):
    items: list[ConversationMessageResponse]
    next_cursor: int | None
