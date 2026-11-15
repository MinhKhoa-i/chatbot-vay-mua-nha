import { API_URL, DATA_UPDATED, USE_MOCK } from "../config.js";
import { maxLoan, schedule } from "./loan.js";

// Lỗi có câu tiếng Việt để hiện thẳng cho người dùng (422 từ backend hoặc kiểm tra ở mock)
export class ApiError extends Error {}

async function request(path, init) {
  const res = await fetch(`${API_URL}${path}`, init);
  if (res.ok) return res.json();
  if (res.status === 422) {
    const body = await res.json().catch(() => null);
    throw new ApiError(typeof body?.detail === "string" ? body.detail : "Thông tin nhập chưa hợp lệ, vui lòng kiểm tra lại.");
  }
  throw new Error("HTTP " + res.status);
}

const delay = (ms) => new Promise((r) => setTimeout(r, ms));

/* Hợp đồng API (khớp docs/api.md, mục 3.2):
   POST {API_URL}/api/chat  { message, session_id }
   ->   { reply, updated_at, estimate?: { amount, years, rate, method?, monthly_payment?, total_interest? } }
   Thiếu monthly_payment thì EstimateCard gọi estimateLoan() để backend tính. */
export async function getReply({ message, sessionId }) {
  if (!USE_MOCK) {
    const res = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  }
  await new Promise((r) => setTimeout(r, 1400));
  return mockReply(message);
}

// GET /api/banks (docs/api.md, mục 3.4) -> { banks[], updated_at, is_sample }
export async function getBanks() {
  if (!USE_MOCK) return request("/api/banks");
  const { default: data } = await import("../../../data/banks_sample.json");
  await delay(300);
  return { banks: data.banks, updated_at: data.updated_at, is_sample: true };
}

// POST /api/estimate (docs/api.md, mục 3.3)
// params: { amount, years, rate, method, promo_rate?, promo_duration_months?,
//           property_value?, monthly_income?, existing_monthly_debt?, max_ltv_percent?, max_dti_percent? }
// Gửi cả property_value và monthly_income thì response có max_loan (hạn mức vay tối đa), không thì null.
export async function estimateLoan(params) {
  const body = { method: "annuity", promo_rate: null, promo_duration_months: 0, ...params };
  if (!USE_MOCK) {
    return request("/api/estimate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }
  await delay(500);
  return mockEstimate(body);
}

// ---- Dữ liệu mẫu (chỉ dùng khi VITE_USE_MOCK=true) ----
// Giống backend/app/main.py: cùng trường trả về, cùng câu báo lỗi
function mockEstimate(body) {
  const { amount, years, rate, method, promo_rate, promo_duration_months } = body;
  if (!Number.isInteger(years) || years < 1 || years > 35) throw new ApiError("Thời hạn vay phải từ 1 đến 35 năm");
  let rows;
  let limit = null;
  try {
    rows = schedule(amount, years * 12, rate, method, promo_rate, promo_duration_months);
    limit = mockMaxLoan(body);
  } catch (e) {
    throw new ApiError(e.message);
  }
  return {
    amount, years, rate, method, promo_rate, promo_duration_months,
    monthly_payment: rows[0].payment,
    total_interest: rows.reduce((t, r) => t + r.interest, 0),
    max_loan: limit,
    updated_at: DATA_UPDATED,
  };
}

function mockMaxLoan(body) {
  const { property_value: value = null, monthly_income: income = null } = body;
  if (value == null && income == null) return null;
  if (value == null || income == null) throw new RangeError("Cần nhập cả giá trị nhà và thu nhập hằng tháng để tính hạn mức vay tối đa");
  const ltv = body.max_ltv_percent ?? 80;
  const dti = body.max_dti_percent ?? 50;
  const result = maxLoan(value, income, body.years * 12, body.rate, body.method, body.promo_rate,
    body.promo_duration_months, 0, body.existing_monthly_debt ?? 0, ltv, dti / 100);
  return { ...result, max_ltv_percent: ltv, max_dti_percent: dti };
}

function parseLoan(text) {
  const m = text.match(/(\d+(?:[.,]\d+)?)\s*(tỷ|tỉ|triệu|tr)(?![\p{L}])/iu);
  const y = text.match(/(\d+)\s*năm/i);
  if (!m || !y) return null;
  const num = parseFloat(m[1].replace(",", "."));
  const amount = /^tr/i.test(m[2]) ? num * 1e6 : num * 1e9;
  return { amount: Math.round(amount), years: parseInt(y[1], 10), rate: 8.5 };
}

const RULES = [
  [/quy trình|các bước|thủ tục|tìm hiểu/i, "Quy trình vay mua nhà gồm 5 giai đoạn:\n1. Chuẩn bị hồ sơ vay vốn\n2. Thẩm định tín dụng và định giá tài sản bảo đảm\n3. Phê duyệt và thông báo kết quả\n4. Ký hợp đồng, đăng ký bảo đảm và giải ngân\n5. Trả nợ định kỳ hoặc tất toán trước hạn"],
  [/điều kiện/i, "Để được xét duyệt, bạn thường cần: đủ độ tuổi theo sản phẩm, mục đích vay hợp pháp, chứng minh được nguồn thu nhập trả nợ và có tài sản bảo đảm nếu sản phẩm yêu cầu. Chỉ có CCCD là chưa đủ để được duyệt."],
  [/hồ sơ/i, "Hồ sơ thường gồm giấy tờ nhân thân, giấy tờ chứng minh thu nhập, hồ sơ pháp lý của nhà hoặc tài sản và phương án vay. Mỗi ngân hàng có thể yêu cầu thêm tùy sản phẩm."],
  [/thả nổi|ưu đãi|lãi suất/i, "Lãi suất thường có giai đoạn ưu đãi cố định, sau đó chuyển sang thả nổi theo lãi suất tham chiếu cộng biên độ. Hết ưu đãi, số tiền trả hàng tháng có thể tăng, nên hãy hỏi kỹ ngân hàng về biên độ và kỳ điều chỉnh."],
  [/trả nợ trước hạn|tất toán/i, "Nhiều ngân hàng thu phí trả nợ trước hạn theo tỷ lệ phần trăm số tiền tất toán, thường giảm dần theo số năm đã vay. Mức phí cụ thể do từng ngân hàng quy định."],
  [/bảo hiểm/i, "Bảo hiểm khoản vay là sản phẩm đi kèm, có thể bắt buộc hoặc tùy chọn tùy ngân hàng. Bạn nên hỏi rõ phạm vi bảo hiểm và mức phí trước khi ký."],
  [/so sánh|ngân hàng/i, "Tính năng so sánh và gợi ý ngân hàng đang được phát triển. Dữ liệu lãi suất, ưu đãi và hạn mức sẽ kèm ngày cập nhật."],
];

function mockReply(message) {
  const loan = parseLoan(message);
  if (loan) {
    const t = loan.amount >= 1e9 ? `${loan.amount / 1e9} tỷ`.replace(".", ",") : `${loan.amount / 1e6} triệu`;
    const reply = `Với khoản vay ${t} đồng trong ${loan.years} năm, bạn có thể tham khảo ước tính bên dưới.`;
    try {
      return { reply, updated_at: DATA_UPDATED, estimate: mockEstimate(loan) };
    } catch (e) {
      return { reply: e.message + ".", updated_at: DATA_UPDATED };
    }
  }
  if (/tính|ước tính|trả hàng tháng|mỗi tháng/i.test(message)) {
    return { reply: "Bạn cho mình biết số tiền muốn vay và thời hạn vay nhé, ví dụ: \"Mình cần vay 1,5 tỷ trong 20 năm\".", updated_at: DATA_UPDATED };
  }
  const hit = RULES.find(([re]) => re.test(message));
  return {
    reply: hit ? hit[1] : "Mình chưa có câu trả lời mẫu cho câu hỏi này. Bạn thử hỏi về quy trình vay, điều kiện vay hoặc nhờ mình tính khoản vay.",
    updated_at: DATA_UPDATED,
  };
}
