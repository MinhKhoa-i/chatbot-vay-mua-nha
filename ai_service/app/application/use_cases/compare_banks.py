import asyncio
from dataclasses import dataclass, replace
from decimal import Decimal

from app.domain.entities.bank_compare_session import BankCompareSession
from app.domain.entities.bank_rank import BankRankRequest, BankRankResult, RankedBank
from app.domain.ports.bank_compare_extractor import BankCompareExtractionError, BankCompareExtractor
from app.domain.ports.bank_ranker import BankRankError, BankRanker
from app.domain.ports.prompt_catalog import PromptCatalog, PromptName

METHOD_TEXT = {
    "annuity": "trả đều gốc + lãi hằng tháng (niên kim)",
    "reducing_balance": "gốc trả đều, lãi tính trên dư nợ giảm dần",
}


@dataclass(frozen=True, slots=True)
class BankCompareTurn:
    answer: str
    session: BankCompareSession
    handled: bool = True
    result: BankRankResult | None = None


class CompareBanksUseCase:
    """Collect a bank comparison scenario and render only backend ranking values."""

    def __init__(self, extractor: BankCompareExtractor, ranker: BankRanker, prompts: PromptCatalog) -> None:
        self._extractor = extractor
        self._ranker = ranker
        self._prompts = prompts

    async def execute(self, text: str, session: BankCompareSession) -> BankCompareTurn:
        extraction = await self._extractor.extract(text, session)
        if extraction.action == "unrelated":
            return BankCompareTurn("", session, handled=False)
        if extraction.action == "cancel":
            return BankCompareTurn(self._prompts.get(PromptName.BANK_COMPARE_CANCELLED), BankCompareSession())

        updated = session.updated(extraction.updates)
        if updated.missing_fields:
            return BankCompareTurn(self._prompts.get(PromptName.BANK_COMPARE_QUESTIONS).format(
                fields=", ".join(self._field_label(name) for name in updated.missing_fields),
            ), updated)
        request = BankRankRequest(
            amount=updated.amount,
            years=updated.years,
            method=updated.method,
            grace_period_months=updated.grace_period_months,
            prepay_month=updated.prepay_month,
            property_value=updated.property_value,
            base_rate=updated.base_rate,
            assumed_floating_rate=updated.assumed_floating_rate,
        )
        try:
            async with asyncio.timeout(10):
                result = await self._ranker.rank(request)
        except TimeoutError as exc:
            raise BankRankError("BANK_RANK_TIMEOUT") from exc
        completed = replace(updated, status="completed")
        return BankCompareTurn(self._render_result(updated, result), completed, result=result)

    @staticmethod
    def _field_label(name: str) -> str:
        return {
            "amount": "số tiền muốn vay (VND)",
            "years": "thời hạn vay (nguyên năm, 1–35)",
            "assumed_floating_rate": "lãi thả nổi giả định (%/năm; bạn tự chọn, mình không tự đặt)",
        }[name]

    def _render_result(self, session: BankCompareSession, result: BankRankResult) -> str:
        ranked_text = "\n".join(
            self._ranked_line(index, bank)
            for index, bank in enumerate(result.ranked, start=1)
        ) or "Không có gói vay nào phù hợp với các điều kiện đầu vào."
        excluded_text = "\n".join(
            f"Không xếp hạng {bank.short_name}: {bank.reason}"
            for bank in result.excluded
        )
        return self._prompts.get(PromptName.BANK_COMPARE_RESULT).format(
            amount=format_vnd(session.amount),
            years=session.years,
            method_text=METHOD_TEXT[session.method],
            prepay_text=(f", trả trước hạn sau {session.prepay_month} tháng" if session.prepay_month else ""),
            grace_text=(f", ân hạn gốc {session.grace_period_months} tháng" if session.grace_period_months else ""),
            property_text=(f", giá trị nhà {format_vnd(session.property_value)} VND"
                           if session.property_value else ""),
            ranked_text=ranked_text,
            excluded_text=excluded_text,
            assumptions_text=self._assumptions_text(result),
            updated_at=result.updated_at,
            sample_note=(" Dữ liệu hiện là dữ liệu mẫu." if result.is_sample else ""),
        )

    @staticmethod
    def _assumptions_text(result: BankRankResult) -> str:
        if not result.assumptions:
            return "Các gói được xếp hạng không cần dùng lãi thả nổi giả định. "
        return "Giả định dùng trong kết quả: " + ", ".join(
            f"{name} = {format_rate(value)}%/năm" for name, value in result.assumptions.items()
        ) + ". "

    @staticmethod
    def _ranked_line(index: int, bank: RankedBank) -> str:
        total_cost = "chưa xác định do chưa rõ phí trả trước" if bank.total_cost is None \
            else f"{format_vnd(bank.total_cost)} VND"
        if bank.prepay_fee is None:
            fee = "phí trả trước chưa rõ"
        elif bank.prepay_fee_is_upper_bound:
            fee = f"phí trả trước tối đa {format_vnd(bank.prepay_fee)} VND"
        else:
            fee = f"phí trả trước {format_vnd(bank.prepay_fee)} VND"
        assumed = f"; ngân hàng này giả định sử dụng lãi thả nổi {format_rate(bank.floating_rate)}%/năm" \
            if bank.floating_rate_assumed and bank.floating_rate is not None else ""
        return (
            f"{index}. {bank.short_name} — {bank.package_name}: tổng chi phí {total_cost}; "
            f"tiền lãi {format_vnd(bank.total_interest)} VND; {fee}; "
            f"khoản trả tháng đầu {format_vnd(bank.first_payment)} VND{assumed}"
        )


def format_vnd(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def format_rate(value: Decimal | int | float | None) -> str:
    if value is None:
        return "chưa rõ"
    return format(Decimal(str(value)).normalize(), "f").replace(".", ",")
