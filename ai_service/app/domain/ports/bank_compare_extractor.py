from typing import Protocol

from app.domain.entities.bank_compare_session import BankCompareExtraction, BankCompareSession
from app.domain.errors import ChatError


class BankCompareExtractionError(ChatError):
    def __init__(self, code: str = "BANK_COMPARE_EXTRACTION_UNAVAILABLE", *, retryable: bool = True) -> None:
        super().__init__(code, stage="bank_compare_extraction", retryable=retryable)


class BankCompareExtractor(Protocol):
    async def extract(self, text: str, session: BankCompareSession) -> BankCompareExtraction: ...
