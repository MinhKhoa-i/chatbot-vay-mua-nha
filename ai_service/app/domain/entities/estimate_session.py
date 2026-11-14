from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Literal

from app.domain.entities.loan_estimate import REPAYMENT_METHODS, LoanEstimateInput

EstimateAction = Literal["update", "confirm", "cancel", "unsupported", "unrelated"]
ESTIMATE_FIELDS = frozenset({"amount", "years", "rate", "method", "promo_rate", "promo_duration_months"})


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_rate(value, name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, float)):
        raise TypeError(f"{name} must be a Decimal or number")
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    if not number.is_finite() or number < 0:
        raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class EstimateSession:
    """Partial loan scenario collected over several chat turns.

    promo_duration_months: None = chưa hỏi ưu đãi, 0 = không có ưu đãi, > 0 = có ưu đãi.
    rate: lãi cả kỳ khi không ưu đãi, hoặc lãi sau ưu đãi khi có ưu đãi.
    """

    amount: int | None = None
    years: int | None = None
    rate: Decimal | None = None
    status: Literal["collecting", "awaiting_confirmation", "completed", "idle"] = "idle"
    method: str | None = None
    promo_rate: Decimal | None = None
    promo_duration_months: int | None = None

    def __post_init__(self) -> None:
        if self.amount is not None and (not _is_int(self.amount) or self.amount <= 0):
            raise ValueError("amount must be a positive integer")
        if self.years is not None and (not _is_int(self.years) or not 1 <= self.years <= 35):
            raise ValueError("years must be an integer from 1 through 35")
        _check_rate(self.rate, "rate")
        _check_rate(self.promo_rate, "promo_rate")
        if self.method is not None and self.method not in REPAYMENT_METHODS:
            raise ValueError("method must be annuity or reducing_balance")
        if self.promo_duration_months is not None and (
                not _is_int(self.promo_duration_months) or self.promo_duration_months < 0):
            raise ValueError("promo_duration_months must be a non-negative integer")
        if self.promo_duration_months == 0 and self.promo_rate is not None:
            raise ValueError("promo_rate requires promo_duration_months")
        if self.status not in {"collecting", "awaiting_confirmation", "completed", "idle"}:
            raise ValueError("Invalid estimate status")
        if self.status in {"awaiting_confirmation", "completed"}:
            if self.missing_fields:
                raise ValueError("Complete estimate data required")
            self.to_input()

    @property
    def active(self) -> bool:
        return self.status in {"collecting", "awaiting_confirmation"}

    @property
    def missing_fields(self) -> tuple[str, ...]:
        missing = [name for name in ("amount", "years", "method") if getattr(self, name) is None]
        if self.promo_duration_months is None and self.promo_rate is None:
            missing.append("promo")
        elif self.promo_duration_months is None:
            missing.append("promo_duration_months")
        elif self.promo_duration_months > 0 and self.promo_rate is None:
            missing.append("promo_rate")
        if self.rate is None:
            missing.append("rate")
        return tuple(missing)

    @property
    def has_promo(self) -> bool:
        return bool(self.promo_duration_months)

    @property
    def promo_exceeds_term(self) -> bool:
        return bool(self.years and self.promo_duration_months
                    and self.promo_duration_months > self.years * 12)

    def updated(self, updates: dict) -> "EstimateSession":
        if not set(updates) <= ESTIMATE_FIELDS:
            raise ValueError("Unknown estimate field")
        values = dict(updates)
        if values.get("promo_duration_months") == 0:
            values["promo_rate"] = None  # khách nói không có ưu đãi
        elif "promo_rate" in values and "promo_duration_months" not in values \
                and self.promo_duration_months == 0:
            values["promo_duration_months"] = None  # trước nói không ưu đãi, giờ có: hỏi lại số tháng
        return replace(self, **values, status="collecting")

    def to_input(self) -> LoanEstimateInput:
        if self.missing_fields:
            raise ValueError("Incomplete estimate")
        return LoanEstimateInput(
            self.amount, self.years, self.rate, self.method, self.promo_rate, self.promo_duration_months,
        )


@dataclass(frozen=True, slots=True)
class EstimateExtraction:
    action: EstimateAction
    updates: dict

    def __post_init__(self) -> None:
        if self.action not in {"update", "confirm", "cancel", "unsupported", "unrelated"}:
            raise ValueError("Unknown extraction action")
        if self.action != "update" and self.updates:
            raise ValueError("Only update actions may modify estimate fields")
        if any(value is None for value in self.updates.values()):
            raise ValueError("Estimate updates must contain explicit values")
        EstimateSession().updated(self.updates)
