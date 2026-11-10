from typing import Protocol
from uuid import UUID

from app.domain.entities.chat_request import ChatClaim, ChatCommit, ChatRequest, ChatSnapshotUpdate
from app.domain.entities.loan_estimate import LoanEstimateResult


class ChatTurnRepository(Protocol):
    async def claim(self, request: ChatRequest, request_hash: str) -> ChatClaim: ...

    async def commit(
        self,
        request: ChatRequest,
        *,
        request_id: UUID,
        lease_token: UUID,
        snapshot_version: int,
        answer: str,
        state_update: ChatSnapshotUpdate | None = None,
        estimate: LoanEstimateResult | None = None,
    ) -> ChatCommit: ...

    async def fail(
        self,
        request: ChatRequest,
        *,
        request_id: UUID,
        lease_token: UUID,
        error_code: str,
        response_status: int,
        retryable: bool,
    ) -> bool: ...
