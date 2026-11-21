from decimal import Decimal

import pytest

from app.domain.entities.bank_compare_session import BankCompareSession
from app.domain.entities.bank_rank import BankRankRequest, BankRankResult, RankedBank


def test_bank_compare_session_does_not_require_assumed_floating_rate():
    session = BankCompareSession(amount=1_500_000_000, years=20)

    assert session.missing_fields == ()
    assert session.complete
    assert session.assumed_floating_rate is None


def test_bank_compare_session_reports_amount_and_years_as_required():
    session = BankCompareSession()

    assert session.missing_fields == ("amount", "years")
    assert not session.complete


def test_bank_compare_session_accepts_explicit_assumed_rate():
    session = BankCompareSession(
        amount=1_500_000_000,
        years=20,
        assumed_floating_rate=Decimal("10"),
    )

    assert session.complete
    assert session.missing_fields == ()


def test_bank_rank_request_preserves_api_defaults_and_nullable_options():
    session = BankCompareSession()
    request = BankRankRequest(amount=1_500_000_000, years=20, assumed_floating_rate=10)

    assert session.method == "annuity"
    assert session.method_explicit is False
    assert request.method == "annuity"
    assert request.grace_period_months == 0
    assert request.prepay_month is None
    assert request.property_value is None
    assert request.base_rate is None


@pytest.mark.parametrize("amount,years", [(True, 20), (0, 20), (100, 0), (100, 36)])
def test_bank_rank_request_rejects_invalid_required_values(amount, years):
    with pytest.raises((TypeError, ValueError)):
        BankRankRequest(amount=amount, years=years)


def test_bank_rank_result_keeps_unknown_total_cost_as_none():
    result = BankRankResult(
        ranked=(RankedBank(
            id="vpbank",
            short_name="VPBank",
            package_name="Gói vay mua nhà",
            total_cost=None,
            total_interest=100_000,
            prepay_fee=None,
            prepay_fee_known=False,
            prepay_fee_is_upper_bound=False,
            first_payment=10_000,
            floating_rate=Decimal("10"),
            floating_rate_assumed=True,
        ),),
        excluded=(),
        assumptions={"floating_rate": Decimal("10")},
        updated_at="2026-11-16",
        is_sample=True,
    )

    assert result.ranked[0].total_cost is None
    assert result.ranked[0].floating_rate_assumed
