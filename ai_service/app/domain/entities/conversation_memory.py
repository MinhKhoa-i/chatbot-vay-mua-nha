from dataclasses import dataclass, replace
from decimal import Decimal

from app.domain.entities.bank_compare_session import BankCompareSession
from app.domain.entities.estimate_session import EstimateSession
from app.domain.entities.loan_estimate import REPAYMENT_METHODS


def _validate_decimal(value: Decimal | None, name: str) -> None:
    if value is not None and (not isinstance(value, Decimal) or not value.is_finite() or value < 0):
        raise ValueError(f"{name} must be a finite non-negative Decimal")


def _format_rate(value: Decimal) -> str:
    return format(value.normalize(), "f").replace(".", ",")


@dataclass(frozen=True, slots=True)
class ConversationMemory:
    """Durable facts retained across turns; transcript remains the source of record."""

    amount: int | None = None
    years: int | None = None
    user_provided_rate: Decimal | None = None
    promo_rate: Decimal | None = None
    promo_duration_months: int | None = None
    repayment_method: str | None = None
    verified_rate: Decimal | None = None
    property_value: int | None = None
    prepay_month: int | None = None
    grace_period_months: int | None = None
    base_rate: Decimal | None = None
    assumed_floating_rate: Decimal | None = None
    source_seq: int | None = None

    def __post_init__(self) -> None:
        if self.amount is not None and (
            not isinstance(self.amount, int) or isinstance(self.amount, bool) or self.amount <= 0
        ):
            raise ValueError("amount must be a positive integer")
        if self.years is not None and (
            not isinstance(self.years, int) or isinstance(self.years, bool) or not 1 <= self.years <= 35
        ):
            raise ValueError("years must be an integer from 1 through 35")
        _validate_decimal(self.user_provided_rate, "user_provided_rate")
        _validate_decimal(self.promo_rate, "promo_rate")
        _validate_decimal(self.verified_rate, "verified_rate")
        _validate_decimal(self.base_rate, "base_rate")
        _validate_decimal(self.assumed_floating_rate, "assumed_floating_rate")
        if self.property_value is not None and (
            not isinstance(self.property_value, int)
            or isinstance(self.property_value, bool)
            or self.property_value <= 0
        ):
            raise ValueError("property_value must be a positive integer")
        for name in ("prepay_month", "grace_period_months"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 0
            ):
                raise ValueError(f"{name} must be a non-negative integer")
        if self.prepay_month == 0:
            raise ValueError("prepay_month must be positive when provided")
        if self.years is not None and self.grace_period_months is not None and (
            self.grace_period_months >= self.years * 12
        ):
            raise ValueError("grace_period_months must be shorter than the loan term")
        if self.years is not None and self.prepay_month is not None and (
            self.prepay_month >= self.years * 12
        ):
            raise ValueError("prepay_month must be shorter than the loan term")
        if self.promo_duration_months is not None and (
            not isinstance(self.promo_duration_months, int)
            or isinstance(self.promo_duration_months, bool)
            or self.promo_duration_months < 0
        ):
            raise ValueError("promo_duration_months must be a non-negative integer")
        if self.promo_duration_months == 0 and self.promo_rate is not None:
            raise ValueError("promo_rate is invalid when there is no promotion")
        if self.repayment_method is not None and self.repayment_method not in REPAYMENT_METHODS:
            raise ValueError("repayment_method is invalid")
        if self.source_seq is not None and (
            not isinstance(self.source_seq, int) or isinstance(self.source_seq, bool) or self.source_seq < 1
        ):
            raise ValueError("source_seq must be a positive integer")

    def merge_estimate(
        self,
        *,
        amount: int | None,
        years: int | None,
        user_provided_rate: Decimal | None,
        promo_rate: Decimal | None,
        promo_duration_months: int | None,
        repayment_method: str | None,
        source_seq: int,
    ) -> "ConversationMemory":
        updated_years = years if years is not None else self.years
        return replace(
            self,
            amount=amount if amount is not None else self.amount,
            years=updated_years,
            user_provided_rate=(
                user_provided_rate if user_provided_rate is not None else self.user_provided_rate
            ),
            promo_rate=promo_rate,
            promo_duration_months=promo_duration_months,
            repayment_method=repayment_method if repayment_method is not None else self.repayment_method,
            prepay_month=(
                self.prepay_month
                if years is None or self.prepay_month is None or self.prepay_month < years * 12
                else None
            ),
            grace_period_months=(
                self.grace_period_months
                if years is None or self.grace_period_months is None
                or self.grace_period_months < years * 12
                else None
            ),
            source_seq=source_seq,
        )

    def merge_bank_comparison(
        self,
        *,
        amount: int | None,
        years: int | None,
        repayment_method: str | None,
        source_seq: int,
        property_value: int | None = None,
        prepay_month: int | None = None,
        grace_period_months: int = 0,
        base_rate: Decimal | None = None,
        assumed_floating_rate: Decimal | None = None,
    ) -> "ConversationMemory":
        updated_years = years if years is not None else self.years
        return replace(
            self,
            amount=amount if amount is not None else self.amount,
            years=updated_years,
            repayment_method=repayment_method if repayment_method is not None else self.repayment_method,
            property_value=property_value,
            prepay_month=(
                prepay_month
                if prepay_month is None or updated_years is None or prepay_month < updated_years * 12
                else None
            ),
            grace_period_months=(
                grace_period_months
                if updated_years is None or grace_period_months < updated_years * 12
                else None
            ),
            base_rate=base_rate,
            assumed_floating_rate=assumed_floating_rate,
            source_seq=source_seq,
        )

    def to_estimate_session(self) -> EstimateSession:
        has_facts = any((
            self.amount, self.years, self.user_provided_rate, self.promo_rate,
            self.promo_duration_months, self.repayment_method,
        ))
        return EstimateSession(
            amount=self.amount,
            years=self.years,
            rate=self.user_provided_rate,
            method=self.repayment_method,
            promo_rate=self.promo_rate,
            promo_duration_months=self.promo_duration_months,
            status="collecting" if has_facts else "idle",
        )

    def to_bank_compare_session(self) -> BankCompareSession:
        return BankCompareSession(
            amount=self.amount,
            years=self.years,
            method=self.repayment_method or "annuity",
            method_explicit=self.repayment_method is not None,
            status="collecting",
        )

    def to_prompt_context(self) -> str:
        facts: list[str] = []
        if self.amount is not None:
            facts.append(f"Số tiền vay người dùng đã nêu: {self.amount:,} VND")
        if self.years is not None:
            facts.append(f"Thời hạn người dùng đã nêu: {self.years} năm")
        if self.repayment_method is not None:
            facts.append(f"Phương thức trả nợ: {self.repayment_method}")
        if self.property_value is not None:
            facts.append(f"Giá trị nhà trong kịch bản so sánh: {self.property_value:,} VND")
        if self.prepay_month is not None:
            facts.append(f"Thời điểm trả trước trong kịch bản so sánh: tháng {self.prepay_month}")
        if self.grace_period_months:
            facts.append(f"Thời gian ân hạn trong kịch bản so sánh: {self.grace_period_months} tháng")
        if self.base_rate is not None:
            facts.append(f"Lãi suất cơ sở giả định trong kịch bản so sánh: {_format_rate(self.base_rate)}%/năm")
        if self.assumed_floating_rate is not None:
            facts.append(
                "Lãi suất thả nổi giả định trong kịch bản so sánh: "
                f"{_format_rate(self.assumed_floating_rate)}%/năm"
            )
        if self.user_provided_rate is not None:
            facts.append(
                f"Lãi suất người dùng cung cấp: {_format_rate(self.user_provided_rate)}%/năm "
                "(chưa xác minh, không phải chính sách ngân hàng)"
            )
        if self.promo_rate is not None:
            duration = (
                f" trong {self.promo_duration_months} tháng"
                if self.promo_duration_months
                else " (chưa rõ thời gian áp dụng)"
            )
            facts.append(
                f"Lãi suất ưu đãi người dùng cung cấp: {_format_rate(self.promo_rate)}%/năm"
                f"{duration} (chưa xác minh)"
            )
        elif self.promo_duration_months:
            facts.append(
                "Thời gian lãi suất ưu đãi người dùng nêu: "
                f"{self.promo_duration_months} tháng (chưa rõ mức lãi suất, chưa xác minh)"
            )
        if self.verified_rate is not None:
            facts.append(
                f"Lãi suất đã được truy xuất từ tài liệu: {_format_rate(self.verified_rate)}%/năm "
                "(vẫn cần kiểm tra điều kiện áp dụng)"
            )
        return "\n".join(facts)
