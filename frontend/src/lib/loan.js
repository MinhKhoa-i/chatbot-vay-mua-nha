export const DEFAULT_RATE = 8.5; // %/năm, giả định minh họa, chưa phải lãi suất ngân hàng cụ thể

// Bản JS của schedule() trong backend/finance/calculator.py, chỉ dùng khi chạy mock.
// Giữ đúng công thức, cách làm tròn và câu báo lỗi của bản Python.
export function schedule(principal, months, annualRate, method = "annuity", promoRate = null, promoMonths = 0) {
  if (!(principal > 0)) throw new RangeError("Số tiền vay phải lớn hơn 0");
  if (!Number.isInteger(months) || months <= 0) throw new RangeError("Số tháng vay phải là số nguyên dương");
  if (annualRate < 0) throw new RangeError("Lãi suất không được âm");
  if (method !== "annuity" && method !== "reducing_balance") throw new RangeError(`Phương thức trả nợ không hợp lệ: ${method}`);
  if (promoRate != null && promoRate < 0) throw new RangeError("Lãi suất ưu đãi không được âm");
  if (!Number.isInteger(promoMonths) || promoMonths < 0) throw new RangeError("Số tháng ưu đãi phải là số nguyên không âm");
  if (promoMonths > months) throw new RangeError("Số tháng ưu đãi không được lớn hơn số tháng vay");
  if (promoRate != null && promoMonths === 0) throw new RangeError("Có lãi suất ưu đãi thì số tháng ưu đãi phải lớn hơn 0");
  if (promoRate == null && promoMonths > 0) throw new RangeError("Có số tháng ưu đãi thì phải nhập lãi suất ưu đãi");

  const rows = [];
  let balance = principal;
  let paidTotal = 0;
  for (let k = 1; k <= months; k++) {
    const r = (k <= promoMonths ? promoRate : annualRate) / 100 / 12;
    const interestF = balance * r;
    const left = months - k + 1;
    const paymentF = method === "annuity"
      ? (r === 0 ? balance / left : (balance * r) / (1 - Math.pow(1 + r, -left)))
      : principal / months + interestF;
    balance -= paymentF - interestF;

    const interest = roundHalfEven(interestF);
    let payment = roundHalfEven(paymentF);
    let paid = payment - interest;
    if (k === months) { paid = principal - paidTotal; payment = paid + interest; }
    paidTotal += paid;
    rows.push({ month: k, payment, interest, principal: paid, balance: Math.round(principal - paidTotal) });
  }
  return rows;
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
