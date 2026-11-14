import pytest

from finance.calculator import (ANNUITY, REDUCING_BALANCE, dti, ltv,
                                max_loan, monthly_payment, schedule, total_interest)

P, N = 1_000_000_000, 240


def test_annuity():
    # 1 tỷ, 20 năm, 10%/năm -> khoảng 9.650.216 đ/tháng
    assert abs(monthly_payment(P, N, 10) - 9_650_216) <= 1
    rows = schedule(P, N, 10)
    assert rows[-1]["balance"] == 0
    assert len({r["payment"] for r in rows[:-1]}) <= 2  # trả đều (sai số làm tròn)


def test_reducing_balance():
    rows = schedule(120_000_000, 12, 12, REDUCING_BALANCE)
    assert rows[0]["payment"] == 10_000_000 + 1_200_000  # gốc 10tr + lãi 1% * 120tr
    assert rows[0]["payment"] > rows[-1]["payment"]


@pytest.mark.parametrize("method", [ANNUITY, REDUCING_BALANCE])
def test_principal_sums_to_loan(method):
    for kwargs in ({}, {"promo_rate": 7, "promo_duration_months": 12}):
        rows = schedule(P, N, 10, method, **kwargs)
        assert sum(r["principal"] for r in rows) == P
        assert rows[-1]["balance"] == 0
        assert all(r["payment"] == r["principal"] + r["interest"] for r in rows)


def test_promo_then_floating():
    promo = schedule(P, N, 11, promo_rate=7, promo_duration_months=12)
    assert promo[0]["payment"] < monthly_payment(P, N, 11)  # ưu đãi rẻ hơn
    assert promo[12]["payment"] > promo[11]["payment"]      # tăng khi thả nổi


def test_zero_rate():
    assert monthly_payment(120_000_000, 12, 0) == 10_000_000


def test_total_interest():
    assert total_interest(120_000_000, 12, 0) == 0
    assert total_interest(P, N, 10) > 0


def test_ltv_dti():
    assert ltv(2_000_000_000, 3_000_000_000) == 2 / 3
    assert dti(15_000_000, 40_000_000) == 0.375


@pytest.mark.parametrize("kwargs, msg", [
    ({"principal": 0}, "Số tiền vay"),
    ({"annual_rate": -5}, "Lãi suất không được âm"),
    ({"months": 240.5}, "số nguyên dương"),
    ({"months": 0}, "số nguyên dương"),
    ({"method": "abc"}, "Phương thức"),
    ({"promo_rate": -1, "promo_duration_months": 6}, "ưu đãi không được âm"),
    ({"promo_rate": 7, "promo_duration_months": 500}, "không được lớn hơn"),
    ({"promo_rate": 7, "promo_duration_months": 0}, "phải lớn hơn 0"),
    ({"promo_duration_months": 12}, "phải nhập lãi suất ưu đãi"),
    ({"promo_rate": 7, "promo_duration_months": 6.5}, "số nguyên không âm"),
    ({"grace_period_months": -1}, "ân hạn gốc phải là số nguyên không âm"),
    ({"grace_period_months": 6.5}, "ân hạn gốc phải là số nguyên không âm"),
    ({"grace_period_months": N}, "ân hạn gốc phải nhỏ hơn số tháng vay"),
    ({"grace_period_months": N + 60}, "ân hạn gốc phải nhỏ hơn số tháng vay"),
])
def test_invalid_input(kwargs, msg):
    args = {"principal": P, "months": N, "annual_rate": 10, **kwargs}
    with pytest.raises(ValueError, match=msg):
        schedule(**args)


@pytest.mark.parametrize("fn, args", [(ltv, (1, 0)), (dti, (1, 0))])
def test_invalid_ratio(fn, args):
    with pytest.raises(ValueError):
        fn(*args)


def _peak(loan, **kw):
    return max(r["payment"] for r in schedule(loan, N, **kw))


def test_max_loan_limited_by_ltv():
    r = max_loan(3_000_000_000, 100_000_000, N, 10)
    assert r["limited_by"] == "ltv"
    assert r["max_loan"] == r["by_ltv"] == 2_400_000_000  # 80% giá trị nhà


def test_max_loan_limited_by_dti():
    r = max_loan(5_000_000_000, 20_000_000, N, 10)  # trả tối đa 50% * 20tr = 10tr/tháng
    assert r["limited_by"] == "dti"
    assert r["max_loan"] == r["by_dti"] < r["by_ltv"]
    assert _peak(r["max_loan"], annual_rate=10) <= 10_000_000
    assert _peak(r["max_loan"] + 1_000_000, annual_rate=10) > 10_000_000  # vừa khít


def test_max_loan_existing_debt():
    base = max_loan(5_000_000_000, 20_000_000, N, 10)["max_loan"]
    less = max_loan(5_000_000_000, 20_000_000, N, 10, existing_monthly_debt=4_000_000)
    assert less["max_loan"] < base
    assert _peak(less["max_loan"], annual_rate=10) <= 6_000_000
    assert max_loan(5_000_000_000, 20_000_000, N, 10, existing_monthly_debt=10_000_000)["max_loan"] == 0


def test_max_loan_reducing_balance_lower_than_annuity():
    a = max_loan(5_000_000_000, 20_000_000, N, 10)["max_loan"]
    b = max_loan(5_000_000_000, 20_000_000, N, 10, REDUCING_BALANCE)["max_loan"]
    assert b < a  # gốc đều: tháng đầu trả cao hơn
    assert _peak(b, annual_rate=10, method=REDUCING_BALANCE) <= 10_000_000


def test_max_loan_promo_uses_peak_payment():
    kw = {"promo_rate": 7, "promo_duration_months": 12}
    r = max_loan(5_000_000_000, 20_000_000, N, 11, **kw)["max_loan"]
    assert _peak(r, annual_rate=11, **kw) <= 10_000_000  # đỉnh sau khi thả nổi vẫn đạt DTI


def test_max_loan_ltv_in_percent():
    assert max_loan(3_000_000_000, 1_000_000_000, N, 10, max_ltv=1)["by_ltv"] == 30_000_000
    assert max_loan(3_000_000_000, 1_000_000_000, N, 10, max_ltv=100)["by_ltv"] == 3_000_000_000
    assert max_loan(3_000_000_000, 1_000_000_000, N, 10, max_ltv=65.5)["by_ltv"] == 1_965_000_000


def test_max_loan_custom_limits():
    r = max_loan(3_000_000_000, 100_000_000, N, 10, max_ltv=70, max_dti=0.4)
    assert r["by_ltv"] == 2_100_000_000
    assert r["by_dti"] < max_loan(3_000_000_000, 100_000_000, N, 10)["by_dti"]


@pytest.mark.parametrize("kwargs, msg", [
    ({"property_value": 0}, "Giá trị tài sản"),
    ({"monthly_income": 0}, "Thu nhập"),
    ({"existing_monthly_debt": -1}, "Nợ hiện tại"),
    ({"max_ltv": 0}, "LTV tối đa"),
    ({"max_ltv": 0.8}, "LTV tối đa"),
    ({"max_ltv": 100.5}, "LTV tối đa"),
    ({"max_ltv": -1}, "LTV tối đa"),
    ({"max_dti": 0}, "DTI tối đa"),
    ({"months": 240.5}, "số nguyên dương"),
    ({"annual_rate": -5}, "Lãi suất không được âm"),
    ({"promo_rate": 7}, "phải lớn hơn 0"),
    ({"grace_period_months": N}, "nhỏ hơn số tháng vay"),
])
def test_max_loan_invalid_input(kwargs, msg):
    args = {"property_value": 3_000_000_000, "monthly_income": 50_000_000,
            "months": N, "annual_rate": 10, **kwargs}
    with pytest.raises(ValueError, match=msg):
        max_loan(**args)


G = 12  # tháng ân hạn dùng trong test


@pytest.mark.parametrize("method", [ANNUITY, REDUCING_BALANCE])
def test_grace_period_interest_only_then_amortize(method):
    rows = schedule(P, N, 10, method, grace_period_months=G)
    after = schedule(P, N - G, 10, method)  # sau ân hạn = vay P trong N - G tháng
    for r in rows[:G]:
        assert r["principal"] == 0 and r["payment"] == r["interest"] == 8_333_333
        assert r["balance"] == P
    assert rows[G]["payment"] == after[0]["payment"]
    assert rows[G]["principal"] == after[0]["principal"]


def test_grace_period_zero_is_default():
    assert schedule(P, N, 10, grace_period_months=0) == schedule(P, N, 10)


@pytest.mark.parametrize("method", [ANNUITY, REDUCING_BALANCE])
def test_grace_period_invariants(method):
    for kwargs in ({"grace_period_months": G},
                   {"promo_rate": 7, "promo_duration_months": 24, "grace_period_months": G},
                   {"promo_rate": 7, "promo_duration_months": 6, "grace_period_months": G},
                   {"grace_period_months": N - 1}):
        rows = schedule(P, N, 10, method, **kwargs)
        assert sum(r["principal"] for r in rows) == P
        assert rows[-1]["balance"] == 0
        assert all(r["payment"] == r["principal"] + r["interest"] for r in rows)


def test_grace_period_costs_more():
    assert total_interest(P, N, 10, grace_period_months=G) > total_interest(P, N, 10)
    assert _peak(P, annual_rate=10, grace_period_months=G) > _peak(P, annual_rate=10)


def test_grace_period_with_promo():
    # ưu đãi 12 tháng trùng ân hạn 12 tháng: 12 tháng đầu chỉ trả lãi 7%
    rows = schedule(P, N, 11, promo_rate=7, promo_duration_months=12, grace_period_months=12)
    assert all(r["payment"] == r["interest"] == 5_833_333 for r in rows[:12])
    assert rows[12]["principal"] > 0


def test_max_loan_grace_period():
    base = max_loan(5_000_000_000, 20_000_000, N, 10)["max_loan"]
    r = max_loan(5_000_000_000, 20_000_000, N, 10, grace_period_months=G)["max_loan"]
    assert r < base  # tiền trả sau ân hạn cao hơn nên vay được ít hơn
    assert _peak(r, annual_rate=10, grace_period_months=G) <= 10_000_000
