export const DEFAULT_RATE = 8.5; // %/năm, giả định minh họa, chưa phải lãi suất ngân hàng cụ thể

// Bản JS của backend/finance/calculator.py (schedule, max_loan), chỉ dùng khi chạy mock.
// Giữ đúng công thức, cách làm tròn và câu báo lỗi của bản Python.
// gracePeriodMonths = grace_period_months: số tháng đầu chỉ trả lãi (ân hạn nợ gốc), nằm trong `months`.
function validate(principal, months, annualRate, method, promoRate, promoMonths, gracePeriodMonths) {
  if (!(principal > 0)) throw new RangeError("Số tiền vay phải lớn hơn 0");
  if (!Number.isInteger(months) || months <= 0) throw new RangeError("Số tháng vay phải là số nguyên dương");
  if (annualRate < 0) throw new RangeError("Lãi suất không được âm");
  if (method !== "annuity" && method !== "reducing_balance") throw new RangeError(`Phương thức trả nợ không hợp lệ: ${method}`);
  if (promoRate != null && promoRate < 0) throw new RangeError("Lãi suất ưu đãi không được âm");
  if (!Number.isInteger(promoMonths) || promoMonths < 0) throw new RangeError("Số tháng ưu đãi phải là số nguyên không âm");
  if (promoMonths > months) throw new RangeError("Số tháng ưu đãi không được lớn hơn số tháng vay");
  if (promoRate != null && promoMonths === 0) throw new RangeError("Có lãi suất ưu đãi thì số tháng ưu đãi phải lớn hơn 0");
  if (promoRate == null && promoMonths > 0) throw new RangeError("Có số tháng ưu đãi thì phải nhập lãi suất ưu đãi");
  if (!Number.isInteger(gracePeriodMonths) || gracePeriodMonths < 0) throw new RangeError("Số tháng ân hạn gốc phải là số nguyên không âm");
  if (gracePeriodMonths >= months) throw new RangeError("Số tháng ân hạn gốc phải nhỏ hơn số tháng vay");
}

// _raw_payments(): [tiền trả, tiền lãi] từng tháng dạng số thực, chưa làm tròn
function* rawPayments(principal, months, annualRate, method, promoRate, promoMonths, gracePeriodMonths) {
  let balance = principal;
  for (let k = 1; k <= months; k++) {
    const r = (k <= promoMonths ? promoRate : annualRate) / 100 / 12;
    const interestF = balance * r;
    const left = months - k + 1;
    const paymentF = k <= gracePeriodMonths
      ? interestF
      : method === "annuity"
        ? (r === 0 ? balance / left : (balance * r) / (1 - Math.pow(1 + r, -left)))
        : principal / (months - gracePeriodMonths) + interestF;
    balance -= paymentF - interestF;
    yield [paymentF, interestF];
  }
}

export function schedule(principal, months, annualRate, method = "annuity", promoRate = null, promoMonths = 0, gracePeriodMonths = 0) {
  validate(principal, months, annualRate, method, promoRate, promoMonths, gracePeriodMonths);
  const rows = [];
  let paidTotal = 0;
  let k = 0;
  for (const [paymentF, interestF] of rawPayments(principal, months, annualRate, method, promoRate, promoMonths, gracePeriodMonths)) {
    k += 1;
    const interest = roundHalfEven(interestF);
    let payment = roundHalfEven(paymentF);
    let paid = payment - interest;
    if (k === months) { paid = principal - paidTotal; payment = paid + interest; }
    paidTotal += paid;
    rows.push({ month: k, payment, interest, principal: paid, balance: Math.round(principal - paidTotal) });
  }
  return rows;
}

// max_loan(): hạn mức vay tối đa = min(theo LTV, theo DTI). maxLtv theo % (80), maxDti theo tỷ lệ (0.5)
export function maxLoan(propertyValue, monthlyIncome, months, annualRate, method = "annuity", promoRate = null,
  promoMonths = 0, gracePeriodMonths = 0, existingMonthlyDebt = 0, maxLtv = 80, maxDti = 0.5) {
  validate(1, months, annualRate, method, promoRate, promoMonths, gracePeriodMonths);
  if (!(propertyValue > 0)) throw new RangeError("Giá trị tài sản phải lớn hơn 0");
  if (!(monthlyIncome > 0)) throw new RangeError("Thu nhập phải lớn hơn 0");
  if (existingMonthlyDebt < 0) throw new RangeError("Nợ hiện tại không được âm");
  if (!(maxLtv >= 1 && maxLtv <= 100)) throw new RangeError("LTV tối đa (%) phải trong khoảng [1, 100], ví dụ 80 = 80%");
  if (!(maxDti > 0 && maxDti <= 1)) throw new RangeError("DTI tối đa phải trong khoảng (0, 1]");
  let unit = -Infinity;
  for (const [p] of rawPayments(1, months, annualRate, method, promoRate, promoMonths, gracePeriodMonths)) unit = Math.max(unit, p);
  const affordable = maxDti * monthlyIncome - existingMonthlyDebt;
  const byLtv = roundHalfEven(propertyValue * maxLtv / 100);
  const byDti = affordable > 0 ? Math.trunc(affordable / unit) : 0;
  return { max_loan: Math.min(byLtv, byDti), by_ltv: byLtv, by_dti: byDti, limited_by: byLtv <= byDti ? "ltv" : "dti" };
}

// round() của Python làm tròn .5 về số chẵn; dùng cùng cách để số mock khớp backend
function roundHalfEven(x) {
  const f = Math.floor(x);
  const d = x - f;
  if (d > 0.5) return f + 1;
  if (d < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}

export const vnd = (n) => new Intl.NumberFormat("vi-VN").format(Math.round(n)) + " đ";
export const fmtDate = (iso) => iso.split("-").reverse().join("/");

// 1500000000 -> "1,5 tỷ", 800000000 -> "800 triệu"
export function shortVnd(n) {
  const fmt = (x) => new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 3 }).format(x);
  if (n >= 1e9) return `${fmt(n / 1e9)} tỷ`;
  if (n >= 1e6) return `${fmt(n / 1e6)} triệu`;
  return vnd(n);
}