import json
from decimal import Decimal

import httpx
import pytest

from app.domain.entities.loan_estimate import LoanEstimateInput
from app.domain.ports.loan_calculator import LoanCalculationError
from app.infrastructure.finance.http_loan_calculator import HttpLoanCalculator


REQUEST = LoanEstimateInput(1_000_000_000, 20, Decimal("8.5"))


def response_payload(**overrides):
    return {
        "amount": REQUEST.amount,
        "years": REQUEST.years,
        "rate": float(REQUEST.rate),
        "monthly_payment": 8_678_232,
        "total_interest": 1_082_775_754,
        "method": "annuity",
        "updated_at": "2026-10-31",
        **overrides,
    }


async def test_posts_existing_backend_contract_and_uses_returned_values():
    def handler(request):
        assert request.method == "POST"
        assert str(request.url) == "http://backend.test/api/estimate"
        assert json.loads(request.content) == {
            "amount": REQUEST.amount, "years": 20, "rate": 8.5,
            "method": "annuity", "promo_rate": None, "promo_duration_months": 0,
        }
        return httpx.Response(200, json=response_payload())

    calculator = HttpLoanCalculator("http://backend.test/", transport=httpx.MockTransport(handler))
    result = await calculator.estimate(REQUEST)
    assert result.request == REQUEST
    assert result.monthly_payment == 8_678_232
    assert result.total_interest == 1_082_775_754
    assert result.updated_at == "2026-10-31"


@pytest.mark.parametrize("overrides", [
    {"amount": 1}, {"years": 10}, {"rate": 9}, {"method": "equal_principal"},
    {"monthly_payment": -1}, {"monthly_payment": True}, {"total_interest": 1.5},
    {"updated_at": None},
])
async def test_rejects_mismatched_or_invalid_backend_results(overrides):
    calculator = HttpLoanCalculator("http://backend.test", transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=response_payload(**overrides)),
    ))
    with pytest.raises(LoanCalculationError) as caught:
        await calculator.estimate(REQUEST)
    assert caught.value.code == "LOAN_CALCULATION_INVALID_RESPONSE"
    assert caught.value.retryable is False


@pytest.mark.parametrize("status", [400, 422, 500, 503])
async def test_http_errors_do_not_expose_backend_response(status):
    calculator = HttpLoanCalculator("http://backend.test", transport=httpx.MockTransport(
        lambda request: httpx.Response(status, text="private backend details"),
    ))
    with pytest.raises(LoanCalculationError) as caught:
        await calculator.estimate(REQUEST)
    assert caught.value.code == "LOAN_CALCULATION_HTTP_ERROR"
    assert "private backend details" not in str(caught.value)


@pytest.mark.parametrize("error, code", [
    (httpx.ReadTimeout, "LOAN_CALCULATION_TIMEOUT"),
    (httpx.ConnectError, "LOAN_CALCULATION_UNAVAILABLE"),
])
async def test_transport_failures_use_safe_domain_errors(error, code):
    def handler(request):
        raise error("private transport details", request=request)

    calculator = HttpLoanCalculator("http://backend.test", transport=httpx.MockTransport(handler))
    with pytest.raises(LoanCalculationError) as caught:
        await calculator.estimate(REQUEST)
    assert caught.value.code == code
    assert caught.value.retryable is True


async def test_invalid_json_is_not_a_successful_estimate():
    calculator = HttpLoanCalculator("http://backend.test", transport=httpx.MockTransport(
        lambda request: httpx.Response(200, text="not json"),
    ))
    with pytest.raises(LoanCalculationError) as caught:
        await calculator.estimate(REQUEST)
    assert caught.value.code == "LOAN_CALCULATION_INVALID_RESPONSE"


PROMO_REQUEST = LoanEstimateInput(1_500_000_000, 20, Decimal("10.3"), "reducing_balance", Decimal("6.8"), 12)


def promo_payload(**overrides):
    return {
        "amount": 1_500_000_000, "years": 20, "rate": 10.3, "method": "reducing_balance",
        "promo_rate": 6.8, "promo_duration_months": 12,
        "monthly_payment": 14_750_000, "total_interest": 1_500_000_000, "updated_at": "2026-10-31",
        **overrides,
    }


async def test_posts_method_and_promo_and_accepts_matching_response():
    def handler(request):
        assert json.loads(request.content) == {
            "amount": 1_500_000_000, "years": 20, "rate": 10.3,
            "method": "reducing_balance", "promo_rate": 6.8, "promo_duration_months": 12,
        }
        return httpx.Response(200, json=promo_payload())

    calculator = HttpLoanCalculator("http://backend.test", transport=httpx.MockTransport(handler))
    result = await calculator.estimate(PROMO_REQUEST)
    assert result.request == PROMO_REQUEST and result.monthly_payment == 14_750_000


@pytest.mark.parametrize("overrides", [
    {"method": "annuity"}, {"promo_rate": 5.0}, {"promo_rate": None}, {"promo_duration_months": 6},
])
async def test_rejects_response_for_different_method_or_promo(overrides):
    calculator = HttpLoanCalculator("http://backend.test", transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=promo_payload(**overrides)),
    ))
    with pytest.raises(LoanCalculationError) as error:
        await calculator.estimate(PROMO_REQUEST)
    assert error.value.code == "LOAN_CALCULATION_INVALID_RESPONSE"
