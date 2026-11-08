import asyncio
from decimal import Decimal

import httpx
import pytest

from app.domain.entities.loan_estimate import LoanEstimateInput
from app.domain.ports.loan_calculator import LoanCalculationError
from app.infrastructure.finance.http_loan_calculator import HttpLoanCalculator


def request() -> LoanEstimateInput:
    return LoanEstimateInput(amount=12_000_000, years=20, rate=Decimal("8.5"))


def valid_payload() -> dict[str, object]:
    return {
        "amount": 12_000_000,
        "years": 20,
        "rate": 8.5,
        "monthly_payment": 104_000,
        "total_interest": 12_960_000,
        "method": "annuity",
        "updated_at": "2026-10-31",
    }


def calculator(handler, *, timeout_seconds: float = 10.0) -> HttpLoanCalculator:
    return HttpLoanCalculator(
        "http://backend.test/",
        timeout_seconds=timeout_seconds,
        transport=httpx.MockTransport(handler),
    )


def test_estimate_posts_contract_and_maps_response():
    seen: list[httpx.Request] = []

    async def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, json=valid_payload())

    result = asyncio.run(calculator(handler).estimate(request()))

    assert len(seen) == 1
    assert str(seen[0].url) == "http://backend.test/api/estimate"
    assert seen[0].method == "POST"
    assert seen[0].read().decode() == '{"amount":12000000,"years":20,"rate":8.5}'
    assert result.request == request()
    assert result.monthly_payment == 104_000
    assert result.total_interest == 12_960_000
    assert result.updated_at == "2026-10-31"


@pytest.mark.parametrize("amount,years,rate", [
    (0, 1, Decimal("0")),
    (-1, 1, Decimal("0")),
    (True, 1, Decimal("0")),
    (1, 0, Decimal("0")),
    (1, 36, Decimal("0")),
    (1, True, Decimal("0")),
    (1, 1, Decimal("-0.1")),
    (1, 1, Decimal("NaN")),
    (1, 1, Decimal("Infinity")),
])
def test_input_rejects_invalid_fields(amount, years, rate):
    with pytest.raises((TypeError, ValueError)):
        LoanEstimateInput(amount=amount, years=years, rate=rate)


@pytest.mark.parametrize("field,value", [
    ("monthly_payment", -1),
    ("monthly_payment", 1.5),
    ("monthly_payment", float("inf")),
    ("monthly_payment", True),
    ("total_interest", -1),
    ("total_interest", 1.5),
    ("total_interest", float("nan")),
    ("total_interest", True),
])
def test_rejects_invalid_money_results(field, value):
    payload = valid_payload()
    payload[field] = value

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with pytest.raises(LoanCalculationError) as error:
        asyncio.run(calculator(handler).estimate(request()))
    assert error.value.stage == "estimate"
    assert error.value.code == "LOAN_CALCULATION_INVALID_RESPONSE"


@pytest.mark.parametrize("change", [
    {"amount": 12_000_001},
    {"years": 21},
    {"rate": 8.6},
    {"method": "unknown"},
    {"updated_at": None},
])
def test_rejects_mismatched_or_incomplete_response(change):
    payload = valid_payload()
    payload.update(change)

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with pytest.raises(LoanCalculationError) as error:
        asyncio.run(calculator(handler).estimate(request()))
    assert error.value.code == "LOAN_CALCULATION_INVALID_RESPONSE"


@pytest.mark.parametrize("payload", [
    [],
    {**valid_payload(), "rate": float("nan")},
    {**valid_payload(), "years": 20.5},
    {**valid_payload(), "monthly_payment": "104000"},
])
def test_rejects_invalid_response_shape_and_numeric_types(payload):
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with pytest.raises(LoanCalculationError) as error:
        asyncio.run(calculator(handler).estimate(request()))
    assert error.value.code == "LOAN_CALCULATION_INVALID_RESPONSE"


def test_timeout_is_sanitized():
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private transport detail")

    with pytest.raises(LoanCalculationError) as error:
        asyncio.run(calculator(handler).estimate(request()))
    assert error.value.code == "LOAN_CALCULATION_TIMEOUT"
    assert error.value.stage == "estimate"
    assert "private transport detail" not in str(error.value)


def test_network_failure_is_sanitized():
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("private transport detail")

    with pytest.raises(LoanCalculationError) as error:
        asyncio.run(calculator(handler).estimate(request()))
    assert error.value.code == "LOAN_CALCULATION_UNAVAILABLE"
    assert "private transport detail" not in str(error.value)


def test_http_status_failure_is_sanitized():
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="private backend detail")

    with pytest.raises(LoanCalculationError) as error:
        asyncio.run(calculator(handler).estimate(request()))
    assert error.value.code == "LOAN_CALCULATION_HTTP_ERROR"
    assert error.value.retryable is False
    assert "private backend detail" not in str(error.value)
