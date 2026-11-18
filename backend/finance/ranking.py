"""Xếp hạng ngân hàng theo tổng chi phí vay (bản nháp).

Tổng chi phí = tiền lãi + phí trả nợ trước hạn.
- Lãi: promo_rate trong promo_duration_months tháng đầu (tối đa bằng số tháng vay), sau đó lãi
  thả nổi theo thứ tự ưu tiên: floating_rate_estimated, base_rate + floating_margin, rồi
  assumed_floating_rate (GIẢ ĐỊNH chung, không phải lãi suất công bố của ngân hàng; kết quả dùng
  nó được đánh dấu floating_rate_assumed=True và ghi trong `assumptions`). Không có cả ba thì
  ngân hàng bị loại (trừ khi ưu đãi phủ hết kỳ hạn). Tính bằng calculator.schedule.
- Không trả trước hạn (prepay_month=None): lãi cả kỳ hạn, phí = 0.
- Trả hết nợ sau prepay_month tháng: lãi đến tháng đó + phí = rate_percent của bậc theo năm * dư nợ
  gốc còn lại. Phí "chưa rõ" (không phải miễn phí) khi early_repayment_penalty.fee_published là
  False, tiers rỗng, hoặc năm trả nợ nằm ngoài các bậc: prepay_fee = None, total_cost = None,
  prepay_fee_known = False; các ngân hàng này được giữ lại nhưng xếp SAU các ngân hàng đã rõ chi phí
  (xếp theo total_interest, là mức chưa gồm phí). Nếu rate_is_upper_bound = True thì rate_percent là
  mức trần: prepay_fee và total_cost là mức TỐI ĐA, đánh dấu prepay_fee_is_upper_bound = True.
- Hòa nhau xếp theo id; thứ tự này không phải khuyến nghị.

Giới hạn của bản nháp: chưa gồm phí khác (bảo hiểm, thẩm định...), phí tối thiểu của ngân hàng;
chưa dùng rate_options (điều kiện là văn bản tự do); chưa xét điều kiện của khách (tuổi, thu nhập).
Ngân hàng không phù hợp thông số vay (thời hạn, số tiền, phương thức, ân hạn, LTV) không được
xếp hạng mà nằm trong `excluded` kèm lý do.
"""

import math

from finance.calculator import ANNUITY, _is_int, _validate, schedule


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _rates(bank, months, base_rate):
    """(lãi ưu đãi, số tháng ưu đãi, lãi thả nổi công bố/suy ra được hoặc None)."""
    ir = bank["interest_rate"]
    promo_rate, promo_months = ir.get("promo_rate"), ir.get("promo_duration_months") or 0
    if promo_rate is None or promo_months == 0:
        promo_rate, promo_months = None, 0
    floating = ir.get("floating_rate_estimated")
    if floating is None and ir.get("floating_margin") is not None and base_rate is not None:
        floating = base_rate + ir["floating_margin"]
    return promo_rate, min(promo_months, months), floating


def _exclusion_reason(bank, principal, months, method, grace_period_months, property_value):
    limit = bank.get("loan_limit", {})
    min_years, max_years = limit.get("min_loan_term_years"), limit.get("max_loan_term_years")
    min_amount, max_amount = limit.get("min_loan_amount"), limit.get("max_loan_amount")
    max_ltv = limit.get("max_ltv_percent")
    if method not in bank.get("repayment_methods", []):
        return f"Không hỗ trợ phương thức trả nợ {method}"
    if min_years and months < min_years * 12:
        return "Thời hạn vay ngắn hơn mức tối thiểu của ngân hàng"
    if max_years and months > max_years * 12:
        return "Thời hạn vay dài hơn mức tối đa của ngân hàng"
    if min_amount and principal < min_amount:
        return "Số tiền vay thấp hơn hạn mức tối thiểu của ngân hàng"
    if max_amount is not None and principal > max_amount:
        return "Số tiền vay vượt hạn mức tối đa của ngân hàng"
    if property_value and max_ltv is not None and principal / property_value * 100 > max_ltv:
        return "Số tiền vay vượt LTV tối đa của ngân hàng"
    if grace_period_months > bank.get("promotions", {}).get("grace_period_months", 0):
        return "Thời gian ân hạn gốc vượt mức ngân hàng cho phép"
    return None


def _fee_percent(bank, month):
    """(phí %, là mức trần?) sau `month` tháng; phí % = None nếu chưa rõ (không phải 0%)."""
    penalty = bank.get("promotions", {}).get("early_repayment_penalty", {})
    if penalty.get("fee_published") is False:
        return None, False
    year = (month - 1) // 12 + 1
    percent = next((t["rate_percent"] for t in penalty.get("tiers") or []
                    if t["from_year"] <= year <= t["to_year"]), None)
    if percent is None:
        return None, False
    return percent, bool(penalty.get("rate_is_upper_bound")) and percent > 0


def _sort_key(item):
    known = item["total_cost"] is not None
    return (not known, item["total_cost"] if known else item["total_interest"], item["id"])


def rank_banks(banks, principal, months, method=ANNUITY, grace_period_months=0,
               prepay_month=None, property_value=None, base_rate=None,
               assumed_floating_rate=None):
    """Xếp hạng `banks` (danh sách theo schema data/banks_sample.json) từ rẻ đến đắt.

    prepay_month : trả hết nợ sau bấy nhiêu tháng (1 .. months - 1); None = giữ đến hết kỳ hạn.
    property_value: giá trị tài sản, có thì loại ngân hàng có LTV tối đa thấp hơn mức cần vay.
    base_rate    : lãi cơ sở (%/năm) để cộng floating_margin khi ngân hàng thiếu lãi thả nổi ước tính.
    assumed_floating_rate: lãi thả nổi GIẢ ĐỊNH (%/năm) cho ngân hàng không công bố lãi thả nổi,
                   để so sánh ưu đãi và phí trên cùng một giả định. None = loại các ngân hàng đó.

    Trả về {"ranked", "excluded", "assumptions"}:
      ranked      : list dict gồm
        id, short_name, package_name                      (str)
        total_cost                                        (VND; None nếu phí trả trước chưa rõ)
        total_interest                                    (VND)
        prepay_fee                                        (VND; 0 nếu không trả trước; None nếu chưa rõ)
        prepay_fee_known                                  (bool; False <=> prepay_fee is None)
        prepay_fee_is_upper_bound                         (bool; True: phí và total_cost là mức tối đa)
        first_payment                                     (VND)
        floating_rate                                     (%/năm dùng để tính sau ưu đãi; None nếu không cần)
        floating_rate_assumed                             (bool; True: floating_rate là giả định chung)
      excluded    : list {"id", "short_name", "reason"}
      assumptions : {"floating_rate": assumed_floating_rate} nếu có ngân hàng dùng giả định, ngược lại {}
    """
    if not _is_number(principal) or principal <= 0:
        raise ValueError("Số tiền vay phải là số lớn hơn 0")
    _validate(principal, months, 0, method, None, 0, grace_period_months)
    if prepay_month is not None and (not _is_int(prepay_month) or not 1 <= prepay_month < months):
        raise ValueError("Tháng trả nợ trước hạn phải là số nguyên từ 1 đến số tháng vay trừ 1")
    if property_value is not None and (not _is_number(property_value) or property_value <= 0):
        raise ValueError("Giá trị tài sản phải là số lớn hơn 0")
    if base_rate is not None and (not _is_number(base_rate) or base_rate < 0):
        raise ValueError("Lãi cơ sở phải là số không âm")
    if assumed_floating_rate is not None and (
            not _is_number(assumed_floating_rate) or assumed_floating_rate < 0):
        raise ValueError("Lãi thả nổi giả định phải là số không âm")

    ranked, excluded = [], []
    for bank in banks:
        promo_rate, promo_months, floating = _rates(bank, months, base_rate)
        needs_floating = promo_months < months
        assumed = floating is None and needs_floating and assumed_floating_rate is not None
        if assumed:
            floating = assumed_floating_rate
        reason = _exclusion_reason(bank, principal, months, method,
                                   grace_period_months, property_value)
        if reason is None and floating is None and needs_floating:
            reason = ("Thiếu lãi suất thả nổi (cần floating_rate_estimated, base_rate + "
                      "floating_margin hoặc assumed_floating_rate)")
        if reason:
            excluded.append({"id": bank["id"], "short_name": bank["short_name"], "reason": reason})
            continue

        rows = schedule(principal, months, promo_rate if floating is None else floating, method,
                        promo_rate, promo_months, grace_period_months)
        k = prepay_month or months
        interest = sum(r["interest"] for r in rows[:k])
        percent, is_cap = _fee_percent(bank, k) if prepay_month else (0.0, False)
        fee = None if percent is None else round(rows[k - 1]["balance"] * percent / 100)
        ranked.append({"id": bank["id"], "short_name": bank["short_name"],
                       "package_name": bank["package_name"],
                       "total_cost": None if fee is None else interest + fee,
                       "total_interest": interest, "prepay_fee": fee,
                       "prepay_fee_known": fee is not None, "prepay_fee_is_upper_bound": is_cap,
                       "first_payment": rows[0]["payment"],
                       "floating_rate": floating, "floating_rate_assumed": assumed})
    ranked.sort(key=_sort_key)
    return {"ranked": ranked, "excluded": excluded,
            "assumptions": {"floating_rate": assumed_floating_rate}
            if any(b["floating_rate_assumed"] for b in ranked) else {}}