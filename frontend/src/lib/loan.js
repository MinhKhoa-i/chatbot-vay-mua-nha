export const DEFAULT_RATE = 8.5; // %/năm, giả định minh họa, chưa phải lãi suất ngân hàng cụ thể

// Trả đều gốc và lãi hằng tháng (niên kim)
export function annuity(amount, years, ratePct = DEFAULT_RATE) {
  const n = years * 12;
  const r = ratePct / 100 / 12;
  const monthly = r === 0 ? amount / n : (amount * r) / (1 - Math.pow(1 + r, -n));
  return { monthly, interest: monthly * n - amount };
}

export const vnd = (n) => new Intl.NumberFormat("vi-VN").format(Math.round(n)) + " đ";
export const fmtDate = (iso) => iso.split("-").reverse().join("/");
