import asyncio
from dataclasses import dataclass, replace
from decimal import Decimal

from app.domain.entities.estimate_session import EstimateSession
from app.domain.entities.loan_estimate import ANNUITY, LoanEstimateInput, LoanEstimateResult
from app.domain.ports.estimate_extractor import EstimateExtractionError, EstimateExtractor
from app.domain.ports.loan_calculator import LoanCalculationError, LoanCalculator
from app.domain.ports.prompt_catalog import PromptCatalog, PromptName

METHOD_TEXT = {
    "annuity": "trả đều gốc + lãi hằng tháng (niên kim)",
    "reducing_balance": "gốc trả đều, lãi tính trên dư nợ giảm dần",
}


def format_vnd(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def format_rate(value: Decimal | int | float) -> str:
    return format(Decimal(str(value)).normalize(), "f").replace(".", ",")


def describe_rate(request: LoanEstimateInput | EstimateSession) -> str:
    if request.promo_duration_months:
        return (f"ưu đãi {format_rate(request.promo_rate)}%/năm "
                f"trong {request.promo_duration_months} tháng đầu, "
                f"sau đó {format_rate(request.rate)}%/năm (giả định giữ nguyên đến hết kỳ)")
    return f"{format_rate(request.rate)}%/năm cố định toàn kỳ"


@dataclass(frozen=True, slots=True)
class EstimateTurn:
    answer: str
    session: EstimateSession
    handled: bool = True
    result: LoanEstimateResult | None = None


class EstimateLoanUseCase:
    """Collect and confirm a loan scenario (method, optional promo) before invoking backend."""

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
            return EstimateTurn(self._render_result(result), replace(session, status="completed"), result=result)
        updated = session.updated(extraction.updates)
        if updated.promo_exceeds_term:
            answer = self._prompts.get(PromptName.ESTIMATE_PROMO_TOO_LONG).format(
                promo_duration_months=updated.promo_duration_months, years=updated.years,
            )
            return EstimateTurn(answer, replace(updated, promo_duration_months=None))
        if updated.missing_fields:
            return EstimateTurn(self._prompts.get(PromptName.ESTIMATE_QUESTIONS).format(
                fields=", ".join(self._field_label(name, updated) for name in updated.missing_fields),
            ), updated)
        updated = replace(updated, status="awaiting_confirmation")
        return EstimateTurn(self._prompts.get(PromptName.ESTIMATE_CONFIRMATION).format(
            amount=format_vnd(updated.amount), years=updated.years,
            rate_text=describe_rate(updated), method_text=METHOD_TEXT[updated.method],
        ), updated)

    @staticmethod
    def _field_label(name: str, session: EstimateSession) -> str:
        if name == "rate":
            return ("lãi suất sau ưu đãi (%/năm, giả định giữ nguyên đến hết kỳ)" if session.has_promo
                    else "lãi suất (%/năm)")
        return {
            "amount": "số tiền muốn vay (VND)",
            "years": "thời hạn vay (nguyên năm, 1–35)",
            "method": "phương thức trả nợ (trả đều gốc + lãi hằng tháng, hay gốc trả đều và lãi giảm dần)",
            "promo": ("khoản vay có lãi suất ưu đãi giai đoạn đầu không "
                      "(nếu có: mức %/năm và số tháng ưu đãi)"),
            "promo_rate": "lãi suất ưu đãi (%/năm)",
            "promo_duration_months": "số tháng hưởng lãi ưu đãi",
        }[name]

    def _render_result(self, result: LoanEstimateResult) -> str:
        request = result.request
        if request.method != ANNUITY:
            payment_label = "Khoản trả tháng đầu (cao nhất, sau đó giảm dần)"
        elif request.promo_duration_months:
            payment_label = "Khoản trả hàng tháng trong thời gian ưu đãi"
        else:
            payment_label = "Khoản trả hàng tháng"
        payment_note = (" Hết thời gian ưu đãi, khoản trả hàng tháng sẽ thay đổi theo lãi sau ưu đãi."
                        if request.promo_duration_months else "")
        return self._prompts.get(PromptName.ESTIMATE_RESULT).format(
            amount=format_vnd(request.amount), years=request.years,
            rate_text=describe_rate(request), method_text=METHOD_TEXT[request.method],
            payment_label=payment_label, monthly_payment=format_vnd(result.monthly_payment),
            total_interest=format_vnd(result.total_interest), payment_note=payment_note,
        )
