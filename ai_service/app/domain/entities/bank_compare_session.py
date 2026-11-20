from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, Literal

from app.domain.entities.loan_estimate import REPAYMENT_METHODS


BankCompareAction = Literal["update", "cancel", "unrelated"]
BANK_COMPARE_FIELDS = frozenset({
    "amount", "years", "assumed_floating_rate", "base_rate", "method", "grace_period_months",
    "property_value", "prepay_month",
})


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
class BankCompareSession:
    """Partial scenario for comparing bank loan packages over chat turns."""

    amount: int | None = None
    years: int | None = None
    assumed_floating_rate: Decimal | None = None
    base_rate: Decimal | None = None
    method: str = "annuity"
    property_value: int | None = None
    prepay_month: int | None = None
    grace_period_months: int = 0
    status: Literal["collecting", "completed", "idle"] = "idle"

    def __post_init__(self) -> None:
        if self.amount is not None and (not _is_int(self.amount) or self.amount <= 0):
            raise ValueError("amount must be a positive integer")
        if self.years is not None and (not _is_int(self.years) or not 1 <= self.years <= 35):
            raise ValueError("years must be an integer from 1 through 35")
        _check_rate(self.assumed_floating_rate, "assumed_floating_rate")
        _check_rate(self.base_rate, "base_rate")
        if self.method not in REPAYMENT_METHODS:
            raise ValueError("method must be annuity or reducing_balance")
        if self.property_value is not None and (
            not _is_int(self.property_value) or self.property_value <= 0
        ):
            raise ValueError("property_value must be a positive integer")
        if not _is_int(self.grace_period_months) or self.grace_period_months < 0 or (
            self.years is not None and self.grace_period_months >= self.years * 12
        ):
            raise ValueError("grace_period_months must be non-negative and shorter than the loan term")
        if self.prepay_month is not None and (
            not _is_int(self.prepay_month) or self.prepay_month <= 0
            or (self.years is not None and self.prepay_month >= self.years * 12)
        ):
            raise ValueError("prepay_month must be positive and shorter than the loan term")
        if self.status not in {"collecting", "completed", "idle"}:
            raise ValueError("Invalid bank comparison status")
        if self.status == "completed" and self.missing_fields:
            raise ValueError("Complete bank comparison data required")

    @property
    def missing_fields(self) -> tuple[str, ...]:
        return tuple(
            name for name in ("amount", "years", "assumed_floating_rate")
            if getattr(self, name) is None
        )

    @property
    def complete(self) -> bool:
        return not self.missing_fields

    @property
    def active(self) -> bool:
        return self.status == "collecting"

    def updated(self, updates: dict[str, Any]) -> "BankCompareSession":
        if not isinstance(updates, dict) or not set(updates) <= BANK_COMPARE_FIELDS:
            raise ValueError("Unknown bank comparison field")
        if any(value is None for value in updates.values()):
            raise ValueError("Bank comparison updates must contain explicit values")
        return replace(self, **updates, status="collecting")


@dataclass(frozen=True, slots=True)
class BankCompareExtraction:
    action: BankCompareAction
    updates: dict[str, Any]

    def __post_init__(self) -> None:
        if self.action not in {"update", "cancel", "unrelated"}:
            raise ValueError("Unknown bank comparison action")
        if self.action != "update" and self.updates:
            raise ValueError("Only update actions may modify bank comparison fields")
        if any(value is None for value in self.updates.values()):
            raise ValueError("Bank comparison updates must contain explicit values")
        BankCompareSession().updated(self.updates)
