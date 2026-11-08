from typing import Protocol

from app.domain.entities.loan_estimate import LoanEstimateInput, LoanEstimateResult
from app.domain.errors import ChatError


class LoanCalculationError(ChatError):
    """Sanitized failure while requesting a loan estimate."""

    def __init__(self, code: str = "LOAN_CALCULATION_UNAVAILABLE", *, retryable: bool = True) -> None:
        super().__init__(code, stage="estimate", retryable=retryable)


class LoanCalculator(Protocol):
    async def estimate(self, request: LoanEstimateInput) -> LoanEstimateResult: ...
