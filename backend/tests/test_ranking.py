import json
from pathlib import Path

import pytest

from finance.calculator import REDUCING_BALANCE, schedule, total_interest
from finance.ranking import rank_banks

P, N = 1_000_000_000, 240
SAMPLE = Path(__file__).resolve().parents[2] / "data" / "banks_sample.json"


def make_bank(id, promo_rate=None, promo_months=None, floating=9.0, margin=None,
              tiers=(), grace=12, methods=("annuity", "reducing_balance"), **limit):
    return {
        "id": id, "short_name": id.upper(), "package_name": f"Gói {id}",
        "interest_rate": {"promo_rate": promo_rate, "promo_duration_months": promo_months,
                          "floating_margin": margin, "floating_rate_estimated": floating},
        "promotions": {"grace_period_months": grace,
                       "early_repayment_penalty": {"tiers": list(tiers)}},
        "loan_limit": {"max_ltv_percent": 80, "max_loan_term_years": 30, "min_loan_term_years": 3,
                       "max_loan_amount": 50_000_000_000, "min_loan_amount": 100_000_000, **limit},
        "repayment_methods": list(methods),
    }


def ids(result):
    return [b["id"] for b in result["ranked"]]


def test_sorted_by_total_cost_and_matches_calculator():
    banks = [make_bank("a", 5, 12, 10), make_bank("b", floating=8), make_bank("c", 6, 36, 9)]
    res = rank_banks(banks, P, N)
    costs = [b["total_cost"] for b in res["ranked"]]
    assert costs == sorted(costs) and len(costs) == 3
    by_id = {b["id"]: b for b in res["ranked"]}
    assert by_id["a"]["total_cost"] == total_interest(P, N, 10, promo_rate=5, promo_duration_months=12)
    assert by_id["b"]["total_cost"] == total_interest(P, N, 8)
    assert by_id["b"]["prepay_fee"] == 0 and by_id["b"]["total_interest"] == by_id["b"]["total_cost"]


def test_promo_rate_duration_and_floating_matter():
    banks = [make_bank("base", 6, 12, 10), make_bank("longer", 6, 36, 10),
             make_bank("lower", 5, 12, 10), make_bank("cheap_float", 6, 12, 9)]
    assert ids(rank_banks(banks, P, N))[-1] == "base"
    res = ids(rank_banks(banks, P, N))
    assert res.index("longer") < res.index("base")
    assert res.index("lower") < res.index("base")
    assert res.index("cheap_float") < res.index("base")


def test_tie_broken_by_id():
    assert ids(rank_banks([make_bank("z"), make_bank("a")], P, N)) == ["a", "z"]


def test_prepayment_fee_flips_ranking():
    fee = [{"from_year": 1, "to_year": 1, "rate_percent": 3.0}]
    banks = [make_bank("low_rate", floating=8, tiers=fee), make_bank("no_fee", floating=8.5)]
    assert ids(rank_banks(banks, P, N)) == ["low_rate", "no_fee"]
    res = rank_banks(banks, P, N, prepay_month=6)
    assert ids(res) == ["no_fee", "low_rate"]
    low = next(b for b in res["ranked"] if b["id"] == "low_rate")
    rows = schedule(P, N, 8)
    assert low["prepay_fee"] == round(rows[5]["balance"] * 3 / 100)
    assert low["total_cost"] == sum(r["interest"] for r in rows[:6]) + low["prepay_fee"]


def test_prepayment_fee_tier_by_year():
    tiers = [{"from_year": 1, "to_year": 1, "rate_percent": 1.5},
             {"from_year": 2, "to_year": 3, "rate_percent": 1.0}]
    bank = make_bank("a", floating=9, tiers=tiers)
    rows = schedule(P, N, 9)
    fee = lambda m: rank_banks([bank], P, N, prepay_month=m)["ranked"][0]["prepay_fee"]
    assert fee(12) == round(rows[11]["balance"] * 1.5 / 100)  # hết năm 1
    assert fee(13) == round(rows[12]["balance"] * 1.0 / 100)  # sang năm 2
    assert fee(60) == 0  # năm 5 ngoài các bậc phí


def test_promo_longer_than_loan_term_is_capped():
    res = rank_banks([make_bank("a", 5, 36, 10, min_loan_term_years=1)], P, 24)
    assert res["ranked"][0]["total_cost"] == total_interest(P, 24, 10, promo_rate=5, promo_duration_months=24)


def test_grace_period_and_method():
    res = rank_banks([make_bank("a", 6, 12, 10)], P, N, REDUCING_BALANCE, grace_period_months=12)
    expected = total_interest(P, N, 10, REDUCING_BALANCE, 6, 12, 12)
    assert res["ranked"][0]["total_cost"] == expected


def test_floating_rate_fallback():
    bank = make_bank("a", 5, 12, floating=None, margin=3.5, min_loan_term_years=1)
    assert rank_banks([bank], P, N)["excluded"][0]["reason"].startswith("Thiếu lãi suất thả nổi")
    res = rank_banks([bank], P, N, base_rate=6)
    assert res["ranked"][0]["floating_rate"] == 9.5
    # ưu đãi phủ hết kỳ hạn thì không cần lãi thả nổi
    assert ids(rank_banks([bank], P, 12)) == ["a"]


@pytest.mark.parametrize("bank_kwargs, call_kwargs, reason", [
    ({"max_loan_term_years": 15}, {}, "Thời hạn vay dài hơn"),
    ({"min_loan_term_years": 25}, {}, "Thời hạn vay ngắn hơn"),
    ({"max_loan_amount": 500_000_000}, {}, "vượt hạn mức tối đa"),
    ({"min_loan_amount": 2_000_000_000}, {}, "thấp hơn hạn mức tối thiểu"),
    ({"methods": ("annuity",)}, {"method": REDUCING_BALANCE}, "Không hỗ trợ phương thức"),
    ({"grace": 0}, {"grace_period_months": 6}, "ân hạn gốc vượt"),
    ({}, {"property_value": 1_100_000_000}, "vượt LTV tối đa"),  # 90.9% > 80%
])
def test_exclusions(bank_kwargs, call_kwargs, reason):
    res = rank_banks([make_bank("bad", **bank_kwargs), make_bank("ok", max_ltv_percent=100)], P, N, **call_kwargs)
    assert ids(res) == ["ok"]
    assert res["excluded"][0]["id"] == "bad" and reason in res["excluded"][0]["reason"]


def test_ltv_within_limit_is_kept():
    assert ids(rank_banks([make_bank("a")], P, N, property_value=1_250_000_000)) == ["a"]  # đúng 80%


@pytest.mark.parametrize("kwargs, msg", [
    ({"principal": 0}, "Số tiền vay"),
    ({"months": 240.5}, "số nguyên dương"),
    ({"grace_period_months": N}, "ân hạn gốc phải nhỏ hơn"),
    ({"prepay_month": 0}, "Tháng trả nợ trước hạn"),
    ({"prepay_month": N}, "Tháng trả nợ trước hạn"),
    ({"prepay_month": 12.5}, "Tháng trả nợ trước hạn"),
    ({"property_value": 0}, "Giá trị tài sản"),
])
def test_invalid_input_even_without_banks(kwargs, msg):
    args = {"banks": [], "principal": P, "months": N, **kwargs}
    with pytest.raises(ValueError, match=msg):
        rank_banks(**args)


def test_no_banks():
    assert rank_banks([], P, N) == {"ranked": [], "excluded": []}


@pytest.mark.skipif(not SAMPLE.exists(), reason="chưa có data/banks_sample.json")
def test_sample_data_every_bank_ranked_or_excluded():
    banks = json.loads(SAMPLE.read_text(encoding="utf-8"))["banks"]
    for kwargs in ({}, {"prepay_month": 36}, {"grace_period_months": 6}):
        res = rank_banks(banks, P, N, base_rate=8, **kwargs)
        assert sorted(ids(res) + [b["id"] for b in res["excluded"]]) == sorted(b["id"] for b in banks)
        costs = [b["total_cost"] for b in res["ranked"]]
        assert costs == sorted(costs)
