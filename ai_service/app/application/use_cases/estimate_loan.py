import asyncio
from dataclasses import dataclass, replace

from app.domain.entities.estimate_session import EstimateSession
from app.domain.entities.loan_estimate import LoanEstimateResult
from app.domain.ports.estimate_extractor import EstimateExtractionError, EstimateExtractor
from app.domain.ports.loan_calculator import LoanCalculationError, LoanCalculator
from app.domain.ports.prompt_catalog import PromptCatalog, PromptName


def format_vnd(value: int) -> str:
    return f"{value:,}".replace(",", ".")


@dataclass(frozen=True, slots=True)
class EstimateTurn:
    answer: str
    session: EstimateSession
    handled: bool = True


class EstimateLoanUseCase:
    """Collect and confirm a fixed-rate annuity scenario before invoking backend."""

    def __init__(self, extractor: EstimateExtractor, calculator: LoanCalculator, prompts: PromptCatalog) -> None:
        self._extractor = extractor
        self._calculator = calculator
        self._prompts = prompts

    async def execute(self, text: str, session: EstimateSession) -> EstimateTurn:
        try:
            async with asyncio.timeout(10):
                extraction = await self._extractor.extract(text, session)
        except TimeoutError as exc:
            raise EstimateExtractionError("ESTIMATE_EXTRACTION_TIMEOUT") from exc
        if extraction.action == "unrelated":
            return EstimateTurn("", session, handled=False)
        if extraction.action == "cancel":
            return EstimateTurn(self._prompts.get(PromptName.ESTIMATE_CANCELLED), EstimateSession())
        if extraction.action == "unsupported":
            return EstimateTurn(self._prompts.get(PromptName.ESTIMATE_UNSUPPORTED), EstimateSession())
        if extraction.action == "confirm" and session.status == "awaiting_confirmation":
            try:
                async with asyncio.timeout(10):
                    result = await self._calculator.estimate(session.to_input())
            except TimeoutError as exc:
                raise LoanCalculationError("LOAN_CALCULATION_TIMEOUT") from exc
            return EstimateTurn(self._render_result(result), replace(session, status="completed"))
        updated = session.updated(extraction.updates)
        if updated.missing_fields:
            return EstimateTurn(self._prompts.get(PromptName.ESTIMATE_QUESTIONS).format(
                fields=", ".join({
                    "amount": "số tiền muốn vay (VND)",
                    "years": "thời hạn vay (nguyên năm, 1–35)",
                    "rate": "lãi suất cố định toàn kỳ (%/năm)",
                }[name] for name in updated.missing_fields),
            ), updated)
        updated = replace(updated, status="awaiting_confirmation")
        return EstimateTurn(self._prompts.get(PromptName.ESTIMATE_CONFIRMATION).format(
            amount=format_vnd(updated.amount), years=updated.years, rate=updated.rate,
        ), updated)

    def _render_result(self, result: LoanEstimateResult) -> str:
        return self._prompts.get(PromptName.ESTIMATE_RESULT).format(
            amount=format_vnd(result.request.amount), years=result.request.years, rate=result.request.rate,
            monthly_payment=format_vnd(result.monthly_payment), total_interest=format_vnd(result.total_interest),
        )
