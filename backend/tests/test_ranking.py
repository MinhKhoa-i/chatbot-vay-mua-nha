import json
from pathlib import Path

import pytest

from finance.calculator import REDUCING_BALANCE, schedule, total_interest
from finance.ranking import rank_banks

P, N = 1_000_000_000, 240
SAMPLE = Path(__file__).resolve().parents[2] / "data" / "banks_sample.json"
FREE = ({"from_year": 1, "to_year": 30, "rate_percent": 0.0},)  # biểu phí đã công bố: miễn phí


def make_bank(id, promo_rate=None, promo_months=None, floating=9.0, margin=None, tiers=FREE,
              grace=12, methods=("annuity", "reducing_balance"), fee_published=None,
              upper_bound=None, **limit):
    penalty = {"tiers": list(tiers), "description": "Nguồn không công bố biểu phí"}
    if fee_published is not None:
        penalty["fee_published"] = fee_published
    if upper_bound is not None:
        penalty["rate_is_upper_bound"] = upper_bound
    return {
        "id": id, "short_name": id.upper(), "package_name": f"Gói {id}",
        "interest_rate": {"promo_rate": promo_rate, "promo_duration_months": promo_months,
                          "floating_margin": margin, "floating_rate_estimated": floating},
        "promotions": {"grace_period_months": grace, "early_repayment_penalty": penalty},
        "loan_limit": {"max_ltv_percent": 80, "max_loan_term_years": 30, "min_loan_term_years": 3,
                       "max_loan_amount": 50_000_000_000, "min_loan_amount": 100_000_000, **limit},
        "repayment_methods": list(methods),
    }


def ids(result):
    return [b["id"] for b in result["ranked"]]


def one(bank, **kwargs):
    return rank_banks([bank], P, N, **kwargs)["ranked"][0]


# ---------- Xếp hạng cơ bản ----------

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
    res = ids(rank_banks(banks, P, N))
    assert res[-1] == "base"
    for better in ("longer", "lower", "cheap_float"):
        assert res.index(better) < res.index("base")


def test_tie_broken_by_id():
    assert ids(rank_banks([make_bank("z"), make_bank("a")], P, N)) == ["a", "z"]


def test_promo_longer_than_loan_term_is_capped():
    res = rank_banks([make_bank("a", 5, 36, 10, min_loan_term_years=1)], P, 24)
    assert res["ranked"][0]["total_cost"] == total_interest(P, 24, 10, promo_rate=5, promo_duration_months=24)


def test_grace_period_and_method():
    res = rank_banks([make_bank("a", 6, 12, 10)], P, N, REDUCING_BALANCE, grace_period_months=12)
    assert res["ranked"][0]["total_cost"] == total_interest(P, N, 10, REDUCING_BALANCE, 6, 12, 12)


def test_no_banks():
    assert rank_banks([], P, N) == {"ranked": [], "excluded": [], "assumptions": {}}


# ---------- Phí trả trước hạn theo bậc năm ----------

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
    assert one(bank, prepay_month=12)["prepay_fee"] == round(rows[11]["balance"] * 1.5 / 100)  # hết năm 1
    assert one(bank, prepay_month=13)["prepay_fee"] == round(rows[12]["balance"] * 1.0 / 100)  # sang năm 2


# ---------- Ý 1: lãi thả nổi giả định ----------

def test_missing_floating_excluded_without_assumption():
    bank = make_bank("a", 5, 12, floating=None)
    res = rank_banks([bank], P, N)
    assert res["ranked"] == [] and res["assumptions"] == {}
    assert res["excluded"][0]["reason"].startswith("Thiếu lãi suất thả nổi")


def test_assumed_floating_rate_is_applied_and_flagged():
    res = rank_banks([make_bank("a", 5, 12, floating=None)], P, N, assumed_floating_rate=10)
    bank = res["ranked"][0]
    assert bank["floating_rate"] == 10 and bank["floating_rate_assumed"] is True
    assert bank["total_cost"] == total_interest(P, N, 10, promo_rate=5, promo_duration_months=12)
    assert res["assumptions"] == {"floating_rate": 10}


def test_assumption_applies_to_banks_without_any_promo():
    bank = one(make_bank("a", floating=None), assumed_floating_rate=10)
    assert bank["floating_rate_assumed"] is True
    assert bank["total_cost"] == total_interest(P, N, 10)


def test_assumption_not_used_when_bank_has_real_rate():
    banks = [make_bank("real", 5, 12, floating=8),
             make_bank("derived", 5, 12, floating=None, margin=3.5),
             make_bank("assumed", 5, 12, floating=None)]
    res = rank_banks(banks, P, N, base_rate=6, assumed_floating_rate=12)
    by_id = {b["id"]: b for b in res["ranked"]}
    assert (by_id["real"]["floating_rate"], by_id["real"]["floating_rate_assumed"]) == (8, False)
    assert (by_id["derived"]["floating_rate"], by_id["derived"]["floating_rate_assumed"]) == (9.5, False)
    assert (by_id["assumed"]["floating_rate"], by_id["assumed"]["floating_rate_assumed"]) == (12, True)


def test_no_assumption_reported_when_none_used():
    res = rank_banks([make_bank("a")], P, N, assumed_floating_rate=12)
    assert res["ranked"][0]["floating_rate_assumed"] is False and res["assumptions"] == {}
    # ưu đãi phủ hết kỳ hạn thì không cần lãi thả nổi, cũng không phải giả định
    covered = make_bank("b", 5, 12, floating=None, min_loan_term_years=1)
    bank = rank_banks([covered], P, 12, assumed_floating_rate=12)["ranked"][0]
    assert bank["floating_rate"] is None and bank["floating_rate_assumed"] is False


def test_same_assumption_makes_promos_comparable():
    banks = [make_bank("long", 5, 24, floating=None), make_bank("short", 5, 6, floating=None)]
    assert ids(rank_banks(banks, P, N, assumed_floating_rate=10)) == ["long", "short"]


# ---------- Ý 2: phí trả trước chưa công bố ----------

def test_unpublished_fee_is_marked_unknown_not_free():
    bank = one(make_bank("a", tiers=()), prepay_month=24)
    assert bank["prepay_fee"] is None and bank["total_cost"] is None
    assert bank["prepay_fee_known"] is False and bank["prepay_fee_is_upper_bound"] is False
    assert bank["total_interest"] == sum(r["interest"] for r in schedule(P, N, 9)[:24])


def test_fee_published_flag_overrides_and_description_is_ignored():
    tiers = [{"from_year": 1, "to_year": 30, "rate_percent": 1.0}]
    assert one(make_bank("a", tiers=tiers, fee_published=False), prepay_month=24)["prepay_fee_known"] is False
    assert one(make_bank("b", tiers=(), fee_published=True), prepay_month=24)["prepay_fee_known"] is False
    # description ghi "không công bố" nhưng dữ liệu có tiers: không dò chữ trong description
    assert one(make_bank("c", tiers=tiers, fee_published=True), prepay_month=24)["prepay_fee_known"] is True


def test_year_outside_tiers_is_unknown_not_free():
    tiers = [{"from_year": 1, "to_year": 3, "rate_percent": 1.0}]
    assert one(make_bank("a", tiers=tiers), prepay_month=60)["prepay_fee"] is None
    assert one(make_bank("a", tiers=tiers), prepay_month=36)["prepay_fee"] is not None


def test_unknown_fee_ignored_when_not_prepaying():
    bank = one(make_bank("a", tiers=()))
    assert bank["prepay_fee"] == 0 and bank["prepay_fee_known"] is True
    assert bank["total_cost"] == bank["total_interest"]


def test_unknown_fee_banks_ranked_after_known_fee_banks():
    banks = [make_bank("cheap_unknown", floating=7, tiers=()), make_bank("dear_known", floating=12),
             make_bank("cheaper_unknown", floating=6, tiers=())]
    assert ids(rank_banks(banks, P, N)) == ["cheaper_unknown", "cheap_unknown", "dear_known"]
    res = rank_banks(banks, P, N, prepay_month=24)
    assert ids(res) == ["dear_known", "cheaper_unknown", "cheap_unknown"]  # đã rõ phí trước, rồi theo lãi


# ---------- Ý 3: phí là mức trần ----------

def test_upper_bound_flag():
    tiers = [{"from_year": 1, "to_year": 4, "rate_percent": 2.5},
             {"from_year": 5, "to_year": 25, "rate_percent": 0.0}]
    cap = make_bank("cap", floating=9, tiers=tiers, upper_bound=True)
    year3 = one(cap, prepay_month=24)
    assert year3["prepay_fee_is_upper_bound"] is True
    assert year3["prepay_fee"] == round(schedule(P, N, 9)[23]["balance"] * 2.5 / 100)
    year6 = one(cap, prepay_month=61)
    assert (year6["prepay_fee"], year6["prepay_fee_is_upper_bound"]) == (0, False)  # miễn phí chính xác


def test_upper_bound_flag_false_when_not_cap_or_not_applicable():
    tiers = [{"from_year": 1, "to_year": 30, "rate_percent": 2.0}]
    assert one(make_bank("a", tiers=tiers), prepay_month=24)["prepay_fee_is_upper_bound"] is False
    assert one(make_bank("b", tiers=tiers, upper_bound=False), prepay_month=24)["prepay_fee_is_upper_bound"] is False
    assert one(make_bank("c", tiers=tiers, upper_bound=True))["prepay_fee_is_upper_bound"] is False  # không trả trước
    assert one(make_bank("d", tiers=(), upper_bound=True), prepay_month=24)["prepay_fee_is_upper_bound"] is False


# ---------- Điều kiện loại ----------

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
    res = rank_banks([make_bank("bad", **bank_kwargs), make_bank("ok", max_ltv_percent=100)],
                     P, N, **call_kwargs)
    assert ids(res) == ["ok"]
    assert res["excluded"][0]["id"] == "bad" and reason in res["excluded"][0]["reason"]


def test_ltv_within_limit_is_kept():
    assert ids(rank_banks([make_bank("a")], P, N, property_value=1_250_000_000)) == ["a"]  # đúng 80%


# ---------- Kiểm tra đầu vào ----------

NAN, INF = float("nan"), float("inf")


@pytest.mark.parametrize("kwargs, msg", [
    ({"principal": 0}, "Số tiền vay phải là số lớn hơn 0"),
    ({"principal": "1e9"}, "Số tiền vay phải là số lớn hơn 0"),
    ({"principal": True}, "Số tiền vay phải là số lớn hơn 0"),
    ({"principal": NAN}, "Số tiền vay phải là số lớn hơn 0"),
    ({"months": 240.5}, "số nguyên dương"),
    ({"grace_period_months": N}, "ân hạn gốc phải nhỏ hơn"),
    ({"prepay_month": 0}, "Tháng trả nợ trước hạn"),
    ({"prepay_month": N}, "Tháng trả nợ trước hạn"),
    ({"prepay_month": 12.5}, "Tháng trả nợ trước hạn"),
    ({"property_value": 0}, "Giá trị tài sản phải là số lớn hơn 0"),
    ({"property_value": -1}, "Giá trị tài sản phải là số lớn hơn 0"),
    ({"property_value": "3e9"}, "Giá trị tài sản phải là số lớn hơn 0"),
    ({"property_value": True}, "Giá trị tài sản phải là số lớn hơn 0"),
    ({"property_value": [3]}, "Giá trị tài sản phải là số lớn hơn 0"),
    ({"property_value": NAN}, "Giá trị tài sản phải là số lớn hơn 0"),
    ({"property_value": INF}, "Giá trị tài sản phải là số lớn hơn 0"),
    ({"base_rate": -50}, "Lãi cơ sở phải là số không âm"),
    ({"base_rate": "6"}, "Lãi cơ sở phải là số không âm"),
    ({"base_rate": True}, "Lãi cơ sở phải là số không âm"),
    ({"base_rate": NAN}, "Lãi cơ sở phải là số không âm"),
    ({"assumed_floating_rate": -1}, "Lãi thả nổi giả định phải là số không âm"),
    ({"assumed_floating_rate": "10"}, "Lãi thả nổi giả định phải là số không âm"),
    ({"assumed_floating_rate": True}, "Lãi thả nổi giả định phải là số không âm"),
    ({"assumed_floating_rate": INF}, "Lãi thả nổi giả định phải là số không âm"),
])
def test_invalid_input_even_without_banks(kwargs, msg):
    args = {"banks": [], "principal": P, "months": N, **kwargs}
    with pytest.raises(ValueError, match=msg):
        rank_banks(**args)


def test_valid_numeric_inputs_accepted():
    res = rank_banks([make_bank("a", floating=None, margin=3.5)], P, N, property_value=2e9,
                     base_rate=0, assumed_floating_rate=0)
    assert res["ranked"][0]["floating_rate"] == 3.5 and res["ranked"][0]["floating_rate_assumed"] is False


# ---------- Dữ liệu thật (data/banks_sample.json) ----------

@pytest.fixture(scope="module")
def sample():
    if not SAMPLE.exists():
        pytest.skip("chưa có data/banks_sample.json")
    return json.loads(SAMPLE.read_text(encoding="utf-8"))["banks"]


def _all_ids(res):
    return sorted(ids(res) + [b["id"] for b in res["excluded"]])


def _no_floating(bank):
    ir = bank["interest_rate"]
    covers = ir.get("promo_rate") is not None and (ir.get("promo_duration_months") or 0) >= N
    return ir.get("floating_rate_estimated") is None and ir.get("floating_margin") is None and not covers


def test_sample_without_assumption_excludes_banks_missing_floating(sample):
    res = rank_banks(sample, P, N)
    assert _all_ids(res) == sorted(b["id"] for b in sample)
    assert sorted(b["id"] for b in res["excluded"] if b["reason"].startswith("Thiếu lãi suất thả nổi")) \
        == sorted(b["id"] for b in sample if _no_floating(b))


@pytest.mark.parametrize("kwargs", [{}, {"prepay_month": 36}, {"prepay_month": 60}, {"grace_period_months": 6}])
def test_sample_all_banks_with_assumption(sample, kwargs):
    res = rank_banks(sample, P, N, assumed_floating_rate=10, **kwargs)
    assert _all_ids(res) == sorted(b["id"] for b in sample)
    assert not any(e["reason"].startswith("Thiếu lãi suất thả nổi") for e in res["excluded"])
    assert res["assumptions"] == ({"floating_rate": 10} if any(b["floating_rate_assumed"] for b in res["ranked"]) else {})
    known = [b["prepay_fee_known"] for b in res["ranked"]]
    assert known == sorted(known, reverse=True)  # ngân hàng đã rõ phí xếp trước
    for b in res["ranked"]:
        assert (b["prepay_fee"] is None) == (b["total_cost"] is None) == (not b["prepay_fee_known"])
        assert b["floating_rate_assumed"] == (b["floating_rate"] == 10)
    costs = [b["total_cost"] for b in res["ranked"] if b["prepay_fee_known"]]
    assert costs == sorted(costs)


def test_sample_empty_tiers_never_treated_as_free(sample):
    res = rank_banks(sample, P, N, assumed_floating_rate=10, prepay_month=24)
    unpublished = {b["id"] for b in sample if not b["promotions"]["early_repayment_penalty"]["tiers"]}
    for b in res["ranked"]:
        if b["id"] in unpublished:
            assert b["prepay_fee"] is None and b["prepay_fee_known"] is False