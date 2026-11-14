from dataclasses import dataclass
from decimal import Decimal

ANNUITY, REDUCING_BALANCE = "annuity", "reducing_balance"
REPAYMENT_METHODS = (ANNUITY, REDUCING_BALANCE)


def _finite_decimal(value: Decimal | int | float, field_name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, float)):
        raise TypeError(f"{field_name} must be a Decimal or number")
    try:
        normalized = value if isinstance(value, Decimal) else Decimal(str(value))
    except (ValueError, ArithmeticError) as exc:
        raise ValueError(f"{field_name} must be finite") from exc
    if not normalized.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return normalized


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True, slots=True)
class LoanEstimateInput:
    """Request for backend POST /api/estimate.

    `rate` is the rate for the whole term, or the rate after the promotion when
    `promo_rate`/`promo_duration_months` are set (same meaning as backend calculator.py).
    """

    amount: int
    years: int
    rate: Decimal
    method: str = ANNUITY
    promo_rate: Decimal | None = None
    promo_duration_months: int = 0

    def __post_init__(self) -> None:
        if not _is_int(self.amount) or self.amount <= 0:
            raise ValueError("amount must be a positive integer")
        if not _is_int(self.years) or not 1 <= self.years <= 35:
            raise ValueError("years must be an integer from 1 through 35")
        rate = _finite_decimal(self.rate, "rate")
        if rate < 0:
            raise ValueError("rate must be non-negative")
        object.__setattr__(self, "rate", rate)
        if self.method not in REPAYMENT_METHODS:
            raise ValueError("method must be annuity or reducing_balance")
        if not _is_int(self.promo_duration_months) or not 0 <= self.promo_duration_months <= self.years * 12:
            raise ValueError("promo_duration_months must be an integer from 0 through the loan term")
        if self.promo_rate is None:
            if self.promo_duration_months:
                raise ValueError("promo_duration_months requires promo_rate")
        else:
            promo_rate = _finite_decimal(self.promo_rate, "promo_rate")
            if promo_rate < 0:
                raise ValueError("promo_rate must be non-negative")
            if not self.promo_duration_months:
                raise ValueError("promo_rate requires promo_duration_months")
            object.__setattr__(self, "promo_rate", promo_rate)


@dataclass(frozen=True, slots=True)
class LoanEstimateResult:
    request: LoanEstimateInput
    monthly_payment: int
    total_interest: int
    updated_at: str

    def __post_init__(self) -> None:
        if not isinstance(self.request, LoanEstimateInput):
            raise TypeError("request must be a LoanEstimateInput")
        for name in ("monthly_payment", "total_interest"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if not isinstance(self.updated_at, str) or not self.updated_at.strip():
            raise ValueError("updated_at must be a non-empty string")
