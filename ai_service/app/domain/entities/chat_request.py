from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.chat_orchestration import ChatIntent


@dataclass(frozen=True, slots=True)
class ChatRequest:
    conversation_id: UUID
    client_request_id: UUID
    text: str
    expected_version: int | None


@dataclass(frozen=True, slots=True)
class ChatSnapshot:
    conversation_version: int
    history: tuple[tuple[str, str], ...]
    lease_token: UUID
    request_id: UUID


@dataclass(frozen=True, slots=True)
class ChatClaim:
    kind: str
    snapshot: ChatSnapshot | None = None
    response_body: dict | None = None
    response_status: int | None = None
    error_code: str | None = None
    retry_after: int | None = None


@dataclass(frozen=True, slots=True)
class ChatCommit:
    response_body: dict
    response_status: int
    user_message_id: UUID | None
    assistant_message_id: UUID | None
    version: int
    error_code: str | None = None
    retryable: bool = False


@dataclass(frozen=True, slots=True)
class ChatSnapshotUpdate:
    intent: ChatIntent


@dataclass(frozen=True, slots=True)
class ChatEvent:
    event: str
    data: dict


class ChatTurnError(RuntimeError):
    def __init__(self, code: str, *, retryable: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
