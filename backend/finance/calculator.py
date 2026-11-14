"""Tính toán khoản vay mua nhà (STT 9: công thức, STT 10: hàm tính).

GHI CHÚ CÔNG THỨC (STT 9)
Quy ước: P = số tiền vay, n = số tháng vay, r = lãi suất năm / 12 (dạng thập phân),
số dư đầu tháng k là B_k (B_1 = P). Đơn vị tiền: VND, lãi suất nhập theo %/năm.

1. Niên kim (trả đều gốc + lãi mỗi tháng):
       PMT = P * r / (1 - (1 + r)^-n)          (r = 0 thì PMT = P / n)
   Lãi tháng k = B_k * r;  gốc tháng k = PMT - lãi.

2. Gốc đều (gốc cố định, lãi giảm dần):
       gốc mỗi tháng = P / n
       trả tháng k  = P / n + B_k * r          (tháng đầu cao nhất, giảm dần)

3. Lãi ưu đãi rồi thả nổi:
   - promo_duration_months (m) tháng đầu dùng lãi ưu đãi, các tháng sau dùng lãi thả nổi
     (lãi thả nổi = lãi cơ sở + biên độ, người dùng nhập sẵn).
   - Khi đổi lãi, tính lại số tiền trả trên dư nợ còn lại và số tháng còn lại:
       niên kim : PMT_mới = B * r_mới / (1 - (1 + r_mới)^-(n - m))
       gốc đều  : gốc vẫn P / n, chỉ lãi đổi theo r_mới
   - Giả định: lãi thả nổi giữ nguyên đến hết kỳ hạn (chỉ là ước tính).

4. Ân hạn nợ gốc (grace_period_months = g, nằm TRONG tổng kỳ hạn n):
   - g tháng đầu chỉ trả lãi: trả = B * r, dư nợ giữ nguyên P.
   - Sau ân hạn trả gốc trong n - g tháng (vẫn có thể đổi lãi theo mục 3):
       niên kim : PMT = B * r / (1 - (1 + r)^-(n - k + 1))   tại tháng k > g
       gốc đều  : gốc mỗi tháng = P / (n - g)
   - Tiền trả hàng tháng sau ân hạn cao hơn mức không ân hạn, tổng lãi cũng cao hơn.

5. LTV (Loan To Value) = khoản vay / giá trị tài sản đảm bảo.
   Ngân hàng thường cho vay tối đa khoảng 70-80% giá trị nhà.

6. DTI (Debt To Income) = (tổng nghĩa vụ trả nợ hàng tháng, gồm khoản vay mới)
                          / thu nhập hàng tháng.
   Thường được xem là an toàn khi DTI <= 50%.
   (Các ngưỡng 70-80% và 50% chỉ là mức tham khảo, cần đối chiếu từng ngân hàng.)

7. Hạn mức vay tối đa = min(theo LTV, theo DTI):
       theo LTV = LTV_max(%) / 100 * giá trị tài sản
       theo DTI = (DTI_max * thu nhập - nợ hiện tại) / u
   Tiền trả hàng tháng tỷ lệ thuận với số tiền vay, nên u = tiền trả tháng CAO NHẤT
   trong kỳ hạn khi vay 1 đồng (thận trọng: gốc đều lấy tháng đầu, ưu đãi rồi thả nổi
   hoặc ân hạn lấy mức sau khi thả nổi / hết ân hạn nếu cao hơn).
"""

ANNUITY, REDUCING_BALANCE = "annuity", "reducing_balance"  # khớp schema dữ liệu
DEFAULT_MAX_LTV, DEFAULT_MAX_DTI = 80, 0.5  # LTV tính theo %, DTI theo tỷ lệ; tham khảo


def _pmt(balance, r, months):
    """Tiền trả hàng tháng theo niên kim cho dư nợ `balance` trong `months` tháng."""
    return balance / months if r == 0 else balance * r / (1 - (1 + r) ** -months)


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _validate(principal, months, annual_rate, method, promo_rate,
              promo_duration_months, grace_period_months):
    if principal <= 0:
        raise ValueError("Số tiền vay phải lớn hơn 0")
    if not _is_int(months) or months <= 0:
        raise ValueError("Số tháng vay phải là số nguyên dương")
    if annual_rate < 0:
        raise ValueError("Lãi suất không được âm")
    if method not in (ANNUITY, REDUCING_BALANCE):
        raise ValueError(f"Phương thức trả nợ không hợp lệ: {method}")
    if promo_rate is not None and promo_rate < 0:
        raise ValueError("Lãi suất ưu đãi không được âm")
    if not _is_int(promo_duration_months) or promo_duration_months < 0:
        raise ValueError("Số tháng ưu đãi phải là số nguyên không âm")
    if promo_duration_months > months:
        raise ValueError("Số tháng ưu đãi không được lớn hơn số tháng vay")
    if promo_rate is not None and promo_duration_months == 0:
        raise ValueError("Có lãi suất ưu đãi thì số tháng ưu đãi phải lớn hơn 0")
    if promo_rate is None and promo_duration_months > 0:
        raise ValueError("Có số tháng ưu đãi thì phải nhập lãi suất ưu đãi")
    if not _is_int(grace_period_months) or grace_period_months < 0:
        raise ValueError("Số tháng ân hạn gốc phải là số nguyên không âm")
    if grace_period_months >= months:
        raise ValueError("Số tháng ân hạn gốc phải nhỏ hơn số tháng vay")


def _raw_payments(principal, months, annual_rate, method, promo_rate,
                  promo_duration_months, grace_period_months):
    """Sinh (tiền trả, tiền lãi) từng tháng dạng số thực, chưa làm tròn."""
    balance = float(principal)
    for k in range(1, months + 1):
        rate = promo_rate if k <= promo_duration_months else annual_rate
        r = rate / 100 / 12
        interest_f = balance * r
        if k <= grace_period_months:  # ân hạn: chỉ trả lãi
            payment_f = interest_f
        elif method == ANNUITY:
            payment_f = _pmt(balance, r, months - k + 1)
        else:
            payment_f = principal / (months - grace_period_months) + interest_f
        balance -= payment_f - interest_f
        yield payment_f, interest_f


def schedule(principal, months, annual_rate, method=ANNUITY,
             promo_rate=None, promo_duration_months=0, grace_period_months=0):
    """Lịch trả nợ: list dict {month, payment, interest, principal, balance}.

    annual_rate: lãi suất thả nổi (%/năm), áp dụng sau thời gian ưu đãi.
    promo_rate : lãi ưu đãi (%/năm), None nếu không có ưu đãi.
    grace_period_months: số tháng đầu chỉ trả lãi (ân hạn nợ gốc), nằm trong `months`.
    Làm tròn đồng; chênh lệch làm tròn dồn vào tháng cuối nên tổng gốc == principal.
    """
    _validate(principal, months, annual_rate, method, promo_rate,
              promo_duration_months, grace_period_months)

    rows, paid_total = [], 0
    for k, (payment_f, interest_f) in enumerate(
            _raw_payments(principal, months, annual_rate, method,
                          promo_rate, promo_duration_months, grace_period_months), 1):
        interest, payment = round(interest_f), round(payment_f)
        paid = payment - interest
        if k == months:  # tháng cuối: trả hết phần gốc còn lại
            paid = principal - paid_total
            payment = paid + interest
        paid_total += paid
        rows.append({"month": k, "payment": payment, "interest": interest,
                     "principal": paid, "balance": round(principal - paid_total)})
    return rows


def monthly_payment(principal, months, annual_rate, method=ANNUITY,
                    promo_rate=None, promo_duration_months=0, grace_period_months=0):
    """Tiền trả tháng đầu tiên (gốc đều: tháng cao nhất; có ân hạn: chỉ gồm lãi)."""
    return schedule(principal, months, annual_rate, method, promo_rate,
                    promo_duration_months, grace_period_months)[0]["payment"]


def total_interest(principal, months, annual_rate, method=ANNUITY,
                   promo_rate=None, promo_duration_months=0, grace_period_months=0):
    """Tổng tiền lãi phải trả trong cả kỳ hạn."""
    rows = schedule(principal, months, annual_rate, method, promo_rate,
                    promo_duration_months, grace_period_months)
    return sum(row["interest"] for row in rows)


def max_loan(property_value, monthly_income, months, annual_rate, method=ANNUITY,
             promo_rate=None, promo_duration_months=0, grace_period_months=0,
             existing_monthly_debt=0, max_ltv=DEFAULT_MAX_LTV, max_dti=DEFAULT_MAX_DTI):
    """Hạn mức vay tối đa (VND, số nguyên) theo LTV và DTI.

    existing_monthly_debt: nghĩa vụ trả nợ hàng tháng hiện có (chưa gồm khoản vay mới).
    max_ltv: LTV tối đa theo % (80 = 80%); max_dti: DTI tối đa theo tỷ lệ (0.5 = 50%).
    Trả về {"max_loan", "by_ltv", "by_dti", "limited_by": "ltv" | "dti"}.
    """
    _validate(1, months, annual_rate, method, promo_rate, promo_duration_months,
              grace_period_months)
    if property_value <= 0:
        raise ValueError("Giá trị tài sản phải lớn hơn 0")
    if monthly_income <= 0:
        raise ValueError("Thu nhập phải lớn hơn 0")
    if existing_monthly_debt < 0:
        raise ValueError("Nợ hiện tại không được âm")
    if not 1 <= max_ltv <= 100:
        raise ValueError("LTV tối đa (%) phải trong khoảng [1, 100], ví dụ 80 = 80%")
    if not 0 < max_dti <= 1:
        raise ValueError("DTI tối đa phải trong khoảng (0, 1]")

    unit = max(p for p, _ in _raw_payments(1, months, annual_rate, method, promo_rate,
                                           promo_duration_months, grace_period_months))
    affordable = max_dti * monthly_income - existing_monthly_debt
    by_ltv = round(property_value * max_ltv / 100)
    by_dti = int(affordable / unit) if affordable > 0 else 0
    return {"max_loan": min(by_ltv, by_dti), "by_ltv": by_ltv, "by_dti": by_dti,
            "limited_by": "ltv" if by_ltv <= by_dti else "dti"}


def ltv(loan, property_value):
    """Tỷ lệ khoản vay / giá trị tài sản (0.7 = 70%)."""
    if property_value <= 0:
        raise ValueError("Giá trị tài sản phải lớn hơn 0")
    return loan / property_value


def dti(monthly_debt, monthly_income):
    """Tỷ lệ nghĩa vụ trả nợ hàng tháng / thu nhập hàng tháng (0.4 = 40%)."""
    if monthly_income <= 0:
        raise ValueError("Thu nhập phải lớn hơn 0")
    return monthly_debt / monthly_income
