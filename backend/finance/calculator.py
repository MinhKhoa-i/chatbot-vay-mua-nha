"""Tính toán khoản vay mua nhà.

GHI CHÚ CÔNG THỨC (Nhiệm vụ 1)
Quy ước: P = số tiền vay, n = số tháng vay, r = lãi suất năm / 12 (dạng thập phân),
số dư đầu tháng k là B_k (B_1 = P). Đơn vị tiền: VND, lãi suất nhập theo %/năm.

1. Niên kim (trả đều gốc + lãi mỗi tháng):
       PMT = P * r / (1 - (1 + r)^-n)          (r = 0 thì PMT = P / n)
   Lãi tháng k = B_k * r;  gốc tháng k = PMT - lãi.

2. Gốc đều (gốc cố định, lãi giảm dần):
       gốc mỗi tháng = P / n
       trả tháng k  = P / n + B_k * r          (tháng đầu cao nhất, giảm dần)

3. Lãi ưu đãi rồi thả nổi:
   - m tháng đầu dùng lãi ưu đãi, các tháng sau dùng lãi thả nổi
     (lãi thả nổi = lãi cơ sở + biên độ, người dùng nhập sẵn).
   - Khi đổi lãi, tính lại số tiền trả trên dư nợ còn lại và số tháng còn lại:
       niên kim : PMT_mới = B * r_mới / (1 - (1 + r_mới)^-(n - m))
       gốc đều  : gốc vẫn P / n, chỉ lãi đổi theo r_mới
   - Giả định: lãi thả nổi giữ nguyên đến hết kỳ hạn (chỉ là ước tính).

4. LTV (Loan To Value) = khoản vay / giá trị tài sản đảm bảo.
   Ngân hàng thường cho vay tối đa khoảng 70-80% giá trị nhà.

5. DTI (Debt To Income) = (tổng nghĩa vụ trả nợ hàng tháng, gồm khoản vay mới)
                          / thu nhập hàng tháng.
   Thường được xem là an toàn khi DTI <= 50%.
   (Các ngưỡng 70-80% và 50% chỉ là mức tham khảo, cần đối chiếu từng ngân hàng.)
"""

ANNUITY, EQUAL_PRINCIPAL = "annuity", "equal_principal"


def _pmt(balance, r, months):
    """Tiền trả hàng tháng theo niên kim cho dư nợ `balance` trong `months` tháng."""
    return balance / months if r == 0 else balance * r / (1 - (1 + r) ** -months)


def schedule(principal, months, annual_rate, method=ANNUITY,
             promo_rate=None, promo_months=0):
    """Lịch trả nợ: list dict {month, payment, interest, principal, balance}.

    annual_rate: lãi suất thả nổi (%/năm), áp dụng sau `promo_months` tháng ưu đãi.
    promo_rate : lãi ưu đãi (%/năm), None nếu không có ưu đãi.
    """
    if principal <= 0 or months <= 0:
        raise ValueError("Số tiền vay và số tháng phải > 0")
    if method not in (ANNUITY, EQUAL_PRINCIPAL):
        raise ValueError(f"Phương thức không hợp lệ: {method}")

    rows, balance = [], principal
    for k in range(1, months + 1):
        rate = promo_rate if promo_rate is not None and k <= promo_months else annual_rate
        r = rate / 100 / 12
        interest = balance * r
        if method == ANNUITY:
            payment = _pmt(balance, r, months - k + 1)
            paid = payment - interest
        else:
            paid = principal / months
            payment = paid + interest
        balance = max(balance - paid, 0.0)
        rows.append({"month": k, "payment": round(payment), "interest": round(interest),
                     "principal": round(paid), "balance": round(balance)})
    return rows


def monthly_payment(principal, months, annual_rate, method=ANNUITY,
                    promo_rate=None, promo_months=0):
    """Tiền trả tháng đầu tiên (gốc đều: tháng cao nhất)."""
    return schedule(principal, months, annual_rate, method, promo_rate, promo_months)[0]["payment"]


def total_interest(principal, months, annual_rate, method=ANNUITY,
                   promo_rate=None, promo_months=0):
    """Tổng tiền lãi phải trả trong cả kỳ hạn."""
    rows = schedule(principal, months, annual_rate, method, promo_rate, promo_months)
    return sum(row["interest"] for row in rows)


def ltv(loan, property_value):
    """Tỷ lệ khoản vay / giá trị tài sản (0.7 = 70%)."""
    if property_value <= 0:
        raise ValueError("Giá trị tài sản phải > 0")
    return loan / property_value


def dti(monthly_debt, monthly_income):
    """Tỷ lệ nghĩa vụ trả nợ hàng tháng / thu nhập hàng tháng (0.4 = 40%)."""
    if monthly_income <= 0:
        raise ValueError("Thu nhập phải > 0")
    return monthly_debt / monthly_income


# ---------- Test (chạy: python calculator.py hoặc pytest calculator.py) ----------

def test_annuity():
    # 1 tỷ, 20 năm, 10%/năm -> khoảng 9.650.216 đ/tháng
    assert abs(monthly_payment(1_000_000_000, 240, 10) - 9_650_216) <= 1
    rows = schedule(1_000_000_000, 240, 10)
    assert rows[-1]["balance"] == 0
    assert len({r["payment"] for r in rows[:-1]}) <= 2  # trả đều (sai số làm tròn)


def test_equal_principal():
    rows = schedule(120_000_000, 12, 12, EQUAL_PRINCIPAL)
    assert rows[0]["payment"] == 10_000_000 + 1_200_000  # gốc 10tr + lãi 1%*120tr
    assert rows[0]["payment"] > rows[-1]["payment"]
    assert sum(r["principal"] for r in rows) == 120_000_000


def test_promo_then_floating():
    args = (1_000_000_000, 240, 11)
    promo = schedule(*args, promo_rate=7, promo_months=12)
    assert promo[0]["payment"] < monthly_payment(*args)            # ưu đãi rẻ hơn
    assert promo[12]["payment"] > promo[11]["payment"]             # tăng khi thả nổi
    assert promo[-1]["balance"] == 0


def test_zero_rate():
    assert monthly_payment(120_000_000, 12, 0) == 10_000_000


def test_ltv_dti():
    assert ltv(2_000_000_000, 3_000_000_000) == 2 / 3
    assert dti(15_000_000, 40_000_000) == 0.375


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("Tất cả test đều đạt")