"""Xếp hạng ngân hàng theo tổng chi phí vay (bản nháp).

Tổng chi phí = tiền lãi + phí trả nợ trước hạn.
- Lãi: promo_rate trong promo_duration_months tháng đầu (tối đa bằng số tháng vay), sau đó
  lãi thả nổi = floating_rate_estimated; nếu thiếu thì base_rate + floating_margin; giữ
  nguyên đến hết kỳ hạn. Tính bằng calculator.schedule (có hỗ trợ ân hạn gốc).
- Không trả trước hạn (prepay_month=None): lãi cả kỳ hạn, phí = 0.
- Trả hết nợ sau prepay_month tháng: lãi đến tháng đó + phí, với
  phí = rate_percent của bậc theo năm trả nợ * dư nợ gốc còn lại. Năm ngoài các bậc phí = 0%.

Giới hạn của bản nháp: chưa gồm phí khác (bảo hiểm, thẩm định...); chưa dùng rate_options
(điều kiện là văn bản tự do); chưa xét điều kiện của khách (tuổi, thu nhập).
Ngân hàng không phù hợp thông số vay (thời hạn, số tiền, phương thức, ân hạn, LTV) không được
xếp hạng mà nằm trong `excluded` kèm lý do.
"""

from finance.calculator import ANNUITY, _is_int, _validate, schedule


def _rates(bank, months, base_rate):
    """(lãi ưu đãi, số tháng ưu đãi, lãi thả nổi hoặc None nếu thiếu dữ liệu)."""
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
    """Phí trả nợ trước hạn (%) tại thời điểm sau `month` tháng."""
    year = (month - 1) // 12 + 1
    tiers = bank.get("promotions", {}).get("early_repayment_penalty", {}).get("tiers", [])
    return next((t["rate_percent"] for t in tiers if t["from_year"] <= year <= t["to_year"]), 0.0)


def rank_banks(banks, principal, months, method=ANNUITY, grace_period_months=0,
               prepay_month=None, property_value=None, base_rate=None):
    """Xếp hạng `banks` (danh sách theo schema data/banks_sample.json) từ rẻ đến đắt.

    prepay_month : trả hết nợ sau bấy nhiêu tháng (1 .. months - 1); None = giữ đến hết kỳ hạn.
    property_value: giá trị tài sản, có thì loại ngân hàng có LTV tối đa thấp hơn mức cần vay.
    base_rate    : lãi cơ sở (%/năm) để cộng floating_margin khi ngân hàng thiếu lãi thả nổi ước tính.
    Trả về {"ranked": [...], "excluded": [{"id", "short_name", "reason"}]}; mỗi phần tử ranked
    có id, short_name, package_name, total_cost, total_interest, prepay_fee, first_payment,
    floating_rate (đơn vị VND, lãi %/năm).
    """
    _validate(principal, months, 0, method, None, 0, grace_period_months)
    if prepay_month is not None and (not _is_int(prepay_month) or not 1 <= prepay_month < months):
        raise ValueError("Tháng trả nợ trước hạn phải là số nguyên từ 1 đến số tháng vay trừ 1")
    if property_value is not None and property_value <= 0:
        raise ValueError("Giá trị tài sản phải lớn hơn 0")

    ranked, excluded = [], []
    for bank in banks:
        promo_rate, promo_months, floating = _rates(bank, months, base_rate)
        reason = _exclusion_reason(bank, principal, months, method,
                                   grace_period_months, property_value)
        if reason is None and floating is None and promo_months < months:
            reason = "Thiếu lãi suất thả nổi (cần floating_rate_estimated hoặc base_rate + floating_margin)"
        if reason:
            excluded.append({"id": bank["id"], "short_name": bank["short_name"], "reason": reason})
            continue

        rows = schedule(principal, months, promo_rate if floating is None else floating, method,
                        promo_rate, promo_months, grace_period_months)
        k = prepay_month or months
        interest = sum(r["interest"] for r in rows[:k])
        fee = round(rows[k - 1]["balance"] * _fee_percent(bank, k) / 100) if prepay_month else 0
        ranked.append({"id": bank["id"], "short_name": bank["short_name"],
                       "package_name": bank["package_name"], "total_cost": interest + fee,
                       "total_interest": interest, "prepay_fee": fee,
                       "first_payment": rows[0]["payment"], "floating_rate": floating})
    ranked.sort(key=lambda b: (b["total_cost"], b["id"]))
    return {"ranked": ranked, "excluded": excluded}
