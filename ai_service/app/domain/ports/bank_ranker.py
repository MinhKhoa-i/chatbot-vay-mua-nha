from typing import Protocol

from app.domain.entities.bank_rank import BankRankRequest, BankRankResult
from app.domain.errors import ChatError


class BankRankError(ChatError):
    """Sanitized failure while requesting a bank ranking."""

    def __init__(
        self,
        code: str = "BANK_RANK_UNAVAILABLE",
        *,
        retryable: bool = True,
        status_code: int = 503,
        detail: str | None = None,
    ) -> None:
        super().__init__(code, stage="bank_rank", retryable=retryable, status_code=status_code)
        self.detail = detail


class BankRanker(Protocol):
    async def rank(self, request: BankRankRequest) -> BankRankResult: ...
