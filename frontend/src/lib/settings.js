import { DEFAULT_RATE } from "./loan.js";

// Cài đặt hiển thị và giá trị mặc định của form (thiết kế V3 - 12).
// Lưu localStorage của trình duyệt này; hội thoại và dữ liệu form thì vẫn chỉ giữ trong bộ nhớ.
const KEY = "tro-ly-vay:cai-dat";
export const FONT_SIZES = { sm: 15, md: 17, lg: 19 }; // px, cỡ chữ tin nhắn
export const DEFAULT_SETTINGS = { fontSize: "md", method: "annuity", rate: DEFAULT_RATE };

export function validRate(r) {
  return Number.isFinite(r) && r >= 0 && r <= 30; // cùng giới hạn với ô lãi suất trên form
}

function sanitize(s) {
  return {
    fontSize: s?.fontSize in FONT_SIZES ? s.fontSize : DEFAULT_SETTINGS.fontSize,
    method: s?.method === "reducing_balance" ? "reducing_balance" : "annuity",
    rate: validRate(s?.rate) ? s.rate : DEFAULT_SETTINGS.rate,
  };
}

export function loadSettings() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? sanitize(JSON.parse(raw)) : DEFAULT_SETTINGS;
  } catch {
    return DEFAULT_SETTINGS; // trình duyệt chặn bộ nhớ hoặc dữ liệu hỏng: dùng mặc định
  }
}

export function saveSettings(s) {
  try { localStorage.setItem(KEY, JSON.stringify(sanitize(s))); } catch { /* không lưu được thì chỉ áp dụng cho lần mở này */ }
}

export function clearSettings() {
  try { localStorage.removeItem(KEY); } catch { /* bỏ qua */ }
}
