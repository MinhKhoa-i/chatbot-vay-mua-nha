import math
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.domain.entities.bank_rank import BankRankRequest, BankRankResult, ExcludedBank, RankedBank
from app.domain.ports.bank_ranker import BankRankError


class HttpBankRanker:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url must be a non-empty string")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) \
                or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = float(timeout_seconds)
        self._transport = transport

    async def rank(self, request: BankRankRequest) -> BankRankResult:
        if not isinstance(request, BankRankRequest):
            raise TypeError("request must be a BankRankRequest")
        url = f"{self._base_url}/api/banks/rank"
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds, transport=self._transport) as client:
                response = await client.post(url, json=self._request_payload(request))
                if response.status_code == 422:
                    detail = self._validation_detail(response)
                    raise BankRankError(
                        "BANK_RANK_INVALID_INPUT", retryable=False, status_code=422, detail=detail,
                    )
                response.raise_for_status()
                payload = response.json()
            return self._parse_response(payload)
        except BankRankError:
            raise
        except httpx.TimeoutException as exc:
            raise BankRankError("BANK_RANK_TIMEOUT") from exc
        except httpx.HTTPStatusError as exc:
            raise BankRankError(
                "BANK_RANK_HTTP_ERROR", retryable=exc.response.status_code >= 500,
                status_code=502,
            ) from exc
        except httpx.RequestError as exc:
            raise BankRankError("BANK_RANK_UNAVAILABLE") from exc
        except (ValueError, TypeError, ArithmeticError, InvalidOperation, OverflowError) as exc:
            raise BankRankError(
                "BANK_RANK_INVALID_RESPONSE", retryable=False, status_code=502,
            ) from exc

    @staticmethod
    def _request_payload(request: BankRankRequest) -> dict[str, Any]:
        return {
            "amount": request.amount,
            "years": request.years,
            "method": request.method,
            "grace_period_months": request.grace_period_months,
            "prepay_month": request.prepay_month,
            "property_value": request.property_value,
            "base_rate": None if request.base_rate is None else float(request.base_rate),
            "assumed_floating_rate": (
                None if request.assumed_floating_rate is None else float(request.assumed_floating_rate)
            ),
        }

    @staticmethod
    def _validation_detail(response: httpx.Response) -> str | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        detail = payload.get("detail") if isinstance(payload, dict) else None
        return detail if isinstance(detail, str) else None

    @classmethod
    def _parse_response(cls, payload: Any) -> BankRankResult:
        if not isinstance(payload, dict):
            raise ValueError("response must be an object")
        ranked_payload = payload.get("ranked")
        excluded_payload = payload.get("excluded")
        assumptions_payload = payload.get("assumptions")
        if not isinstance(ranked_payload, list) or not isinstance(excluded_payload, list):
            raise ValueError("ranked and excluded must be arrays")
        if not isinstance(assumptions_payload, dict):
            raise ValueError("assumptions must be an object")
        if not isinstance(payload.get("updated_at"), str) or not isinstance(payload.get("is_sample"), bool):
            raise ValueError("updated_at or is_sample has an invalid type")
        ranked = tuple(cls._parse_ranked_bank(item) for item in ranked_payload)
        excluded = tuple(cls._parse_excluded_bank(item) for item in excluded_payload)
        assumptions = {
            name: cls._parse_number(value, f"assumptions.{name}")
            for name, value in assumptions_payload.items()
        }
        return BankRankResult(
            ranked=ranked,
            excluded=excluded,
            assumptions=assumptions,
            updated_at=payload["updated_at"],
            is_sample=payload["is_sample"],
        )

    @classmethod
    def _parse_ranked_bank(cls, payload: Any) -> RankedBank:
        if not isinstance(payload, dict):
            raise ValueError("ranked bank must be an object")
        return RankedBank(
            id=cls._parse_string(payload.get("id"), "id"),
            short_name=cls._parse_string(payload.get("short_name"), "short_name"),
            package_name=cls._parse_string(payload.get("package_name"), "package_name"),
            total_cost=cls._optional_integer(payload.get("total_cost"), "total_cost"),
            total_interest=cls._parse_integer(payload.get("total_interest"), "total_interest"),
            prepay_fee=cls._optional_integer(payload.get("prepay_fee"), "prepay_fee"),
            prepay_fee_known=cls._parse_bool(payload.get("prepay_fee_known"), "prepay_fee_known"),
            prepay_fee_is_upper_bound=cls._parse_bool(
                payload.get("prepay_fee_is_upper_bound"), "prepay_fee_is_upper_bound",
            ),
            first_payment=cls._parse_integer(payload.get("first_payment"), "first_payment"),
            floating_rate=cls._optional_number(payload.get("floating_rate"), "floating_rate"),
            floating_rate_assumed=cls._parse_bool(
                payload.get("floating_rate_assumed"), "floating_rate_assumed",
            ),
        )

    @classmethod
    def _parse_excluded_bank(cls, payload: Any) -> ExcludedBank:
        if not isinstance(payload, dict):
            raise ValueError("excluded bank must be an object")
        return ExcludedBank(
            id=cls._parse_string(payload.get("id"), "id"),
            short_name=cls._parse_string(payload.get("short_name"), "short_name"),
            reason=cls._parse_string(payload.get("reason"), "reason"),
        )

    @staticmethod
    def _parse_string(value: Any, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value

    @staticmethod
    def _parse_bool(value: Any, name: str) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be a boolean")
        return value

    @classmethod
    def _parse_number(cls, value: Any, name: str) -> Decimal:
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError(f"{name} must be numeric")
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"{name} must be finite numeric") from exc
        if not number.is_finite() or number < 0:
            raise ValueError(f"{name} must be finite and non-negative")
        return number

    @classmethod
    def _parse_integer(cls, value: Any, name: str) -> int:
        number = cls._parse_number(value, name)
        if number != number.to_integral_value():
            raise ValueError(f"{name} must be an integer")
        return int(number)

    @classmethod
    def _optional_integer(cls, value: Any, name: str) -> int | None:
        return None if value is None else cls._parse_integer(value, name)

    @classmethod
    def _optional_number(cls, value: Any, name: str) -> Decimal | None:
        return None if value is None else cls._parse_number(value, name)
