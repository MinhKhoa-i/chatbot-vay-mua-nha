import json
import math
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.domain.entities.loan_estimate import LoanEstimateInput, LoanEstimateResult
from app.domain.ports.loan_calculator import LoanCalculationError


class HttpLoanCalculator:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url must be a non-empty string")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) \
                or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = float(timeout_seconds)
        self._transport = transport

    async def estimate(self, request: LoanEstimateInput) -> LoanEstimateResult:
        if not isinstance(request, LoanEstimateInput):
            raise TypeError("request must be a LoanEstimateInput")
        url = f"{self._base_url}/api/estimate"
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds, transport=self._transport) as client:
                response = await client.post(url, json={
                    "amount": request.amount,
                    "years": request.years,
                    "rate": float(request.rate),
                })
                response.raise_for_status()
                payload = response.json()
            return self._parse_response(payload, request)
        except httpx.TimeoutException as exc:
            raise LoanCalculationError("LOAN_CALCULATION_TIMEOUT") from exc
        except httpx.HTTPStatusError as exc:
            raise LoanCalculationError("LOAN_CALCULATION_HTTP_ERROR", retryable=False) from exc
        except httpx.RequestError as exc:
            raise LoanCalculationError("LOAN_CALCULATION_UNAVAILABLE") from exc
        except (ValueError, TypeError, ArithmeticError, InvalidOperation, OverflowError) as exc:
            raise LoanCalculationError("LOAN_CALCULATION_INVALID_RESPONSE", retryable=False) from exc

    @classmethod
    def _parse_response(cls, payload: Any, request: LoanEstimateInput) -> LoanEstimateResult:
        if not isinstance(payload, dict):
            raise ValueError("response must be an object")
        amount = cls._parse_number(payload.get("amount"), "amount")
        years = cls._parse_integer(payload.get("years"), "years")
        rate = cls._parse_number(payload.get("rate"), "rate")
        if amount != Decimal(request.amount) or years != request.years or rate != request.rate:
            raise ValueError("response does not match request")
        if payload.get("method") != "annuity":
            raise ValueError("unexpected calculation method")
        return LoanEstimateResult(
            request=request,
            monthly_payment=cls._parse_integer(payload.get("monthly_payment"), "monthly_payment"),
            total_interest=cls._parse_integer(payload.get("total_interest"), "total_interest"),
            updated_at=payload.get("updated_at"),
        )

    @staticmethod
    def _parse_number(value: Any, name: str) -> Decimal:
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError(f"{name} must be numeric")
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"{name} must be finite numeric") from exc
        if not number.is_finite():
            raise ValueError(f"{name} must be finite numeric")
        return number

    @classmethod
    def _parse_integer(cls, value: Any, name: str) -> int:
        number = cls._parse_number(value, name)
        if number < 0 or number != number.to_integral_value():
            raise ValueError(f"{name} must be a non-negative integer")
        return int(number)
