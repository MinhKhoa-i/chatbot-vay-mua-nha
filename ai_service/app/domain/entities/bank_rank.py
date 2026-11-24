from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.domain.entities.loan_estimate import REPAYMENT_METHODS


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_rate(value: Any, name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, float)):
        raise TypeError(f"{name} must be a Decimal or number")
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    if not number.is_finite() or number < 0:
        raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class BankRankRequest:
    """Request contract for backend POST /api/banks/rank."""

    amount: int
    years: int
    method: str = "annuity"
    grace_period_months: int = 0
    prepay_month: int | None = None
    property_value: int | None = None
    base_rate: Decimal | None = None
    assumed_floating_rate: Decimal | None = None

    def __post_init__(self) -> None:
        if not _is_int(self.amount) or self.amount <= 0:
            raise ValueError("amount must be a positive integer")
        if not _is_int(self.years) or not 1 <= self.years <= 35:
            raise ValueError("years must be an integer from 1 through 35")
        if self.method not in REPAYMENT_METHODS:
            raise ValueError("method must be annuity or reducing_balance")
        if not _is_int(self.grace_period_months) or not 0 <= self.grace_period_months < self.years * 12:
            raise ValueError("grace_period_months must be non-negative and shorter than the loan term")
        if self.prepay_month is not None and (
            not _is_int(self.prepay_month) or not 1 <= self.prepay_month < self.years * 12
        ):
            raise ValueError("prepay_month must be between 1 and the loan term minus one month")
        if self.property_value is not None and (
            not _is_int(self.property_value) or self.property_value <= 0
        ):
            raise ValueError("property_value must be a positive integer")
        _check_rate(self.base_rate, "base_rate")
        _check_rate(self.assumed_floating_rate, "assumed_floating_rate")


@dataclass(frozen=True, slots=True)
class RankedBank:
    id: str
    short_name: str
    package_name: str
    total_cost: int | None
    total_interest: int
    prepay_fee: int | None
    prepay_fee_known: bool
    prepay_fee_is_upper_bound: bool
    first_payment: int
    floating_rate: Decimal | None
    floating_rate_assumed: bool

    def __post_init__(self) -> None:
        for name in ("id", "short_name", "package_name"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        for name in ("total_cost", "total_interest", "prepay_fee", "first_payment"):
            value = getattr(self, name)
            if value is not None and (not _is_int(value) or value < 0):
                raise ValueError(f"{name} must be a non-negative integer or None")
        for name in ("prepay_fee_known", "prepay_fee_is_upper_bound", "floating_rate_assumed"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a boolean")
        _check_rate(self.floating_rate, "floating_rate")


@dataclass(frozen=True, slots=True)
class ExcludedBank:
    id: str
    short_name: str
    reason: str

    def __post_init__(self) -> None:
        for name in ("id", "short_name", "reason"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class BankRankResult:
    ranked: tuple[RankedBank, ...]
    excluded: tuple[ExcludedBank, ...]
    assumptions: dict[str, Decimal]
    updated_at: str
    is_sample: bool

    def __post_init__(self) -> None:
        if not isinstance(self.ranked, tuple) or not all(isinstance(bank, RankedBank) for bank in self.ranked):
            raise TypeError("ranked must be a tuple of RankedBank")
        if not isinstance(self.excluded, tuple) or not all(
            isinstance(bank, ExcludedBank) for bank in self.excluded
        ):
            raise TypeError("excluded must be a tuple of ExcludedBank")
        if not isinstance(self.assumptions, dict) or any(
            not isinstance(name, str) for name in self.assumptions
        ):
            raise TypeError("assumptions must be a string-keyed dictionary")
        for name, value in self.assumptions.items():
            _check_rate(value, name)
        if not isinstance(self.updated_at, str) or not self.updated_at.strip():
            raise ValueError("updated_at must be a non-empty string")
        if not isinstance(self.is_sample, bool):
            raise TypeError("is_sample must be a boolean")
