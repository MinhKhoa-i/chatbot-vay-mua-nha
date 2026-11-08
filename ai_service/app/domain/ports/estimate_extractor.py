from typing import Protocol

from app.domain.entities.estimate_session import EstimateExtraction, EstimateSession
from app.domain.errors import ChatError


class EstimateExtractionError(ChatError):
    def __init__(self, code: str = "ESTIMATE_EXTRACTION_UNAVAILABLE", *, retryable: bool = True) -> None:
        super().__init__(code, stage="estimate_extraction", retryable=retryable)


class EstimateExtractor(Protocol):
    async def extract(
        self, text: str, session: EstimateSession,
    ) -> EstimateExtraction: ...
