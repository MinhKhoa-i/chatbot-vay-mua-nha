from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Literal

from app.domain.entities.loan_estimate import LoanEstimateInput

EstimateAction = Literal["update", "confirm", "cancel", "unsupported", "unrelated"]


@dataclass(frozen=True, slots=True)
class EstimateSession:
    amount: int | None = None
    years: int | None = None
    rate: Decimal | None = None
    status: Literal["collecting", "awaiting_confirmation", "completed", "idle"] = "idle"

    def __post_init__(self) -> None:
        # Validate partial data using the same rules as the calculator request.
        LoanEstimateInput(
            self.amount if self.amount is not None else 1,
            self.years if self.years is not None else 1,
            self.rate if self.rate is not None else Decimal(0),
        )
        if self.status not in {"collecting", "awaiting_confirmation", "completed", "idle"}:
            raise ValueError("Invalid estimate status")
        if self.status in {"awaiting_confirmation", "completed"} and self.missing_fields:
            raise ValueError("Complete estimate data required")

    @property
    def active(self) -> bool:
        return self.status in {"collecting", "awaiting_confirmation"}

    @property
    def missing_fields(self) -> tuple[str, ...]:
        return tuple(name for name in ("amount", "years", "rate") if getattr(self, name) is None)

    def updated(self, updates: dict) -> "EstimateSession":
        if not set(updates) <= {"amount", "years", "rate"}:
            raise ValueError("Unknown estimate field")
        return replace(self, **updates, status="collecting")

    def to_input(self) -> LoanEstimateInput:
        if self.missing_fields:
            raise ValueError("Incomplete estimate")
        return LoanEstimateInput(self.amount, self.years, self.rate)


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
