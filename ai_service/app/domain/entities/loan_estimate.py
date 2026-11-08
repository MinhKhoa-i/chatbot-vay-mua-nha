from dataclasses import dataclass
from decimal import Decimal


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


@dataclass(frozen=True, slots=True)
class LoanEstimateInput:
    amount: int
    years: int
    rate: Decimal

    def __post_init__(self) -> None:
        if isinstance(self.amount, bool) or not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError("amount must be a positive integer")
        if isinstance(self.years, bool) or not isinstance(self.years, int) or not 1 <= self.years <= 35:
            raise ValueError("years must be an integer from 1 through 35")
        rate = _finite_decimal(self.rate, "rate")
        if rate < 0:
            raise ValueError("rate must be non-negative")
        object.__setattr__(self, "rate", rate)


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
