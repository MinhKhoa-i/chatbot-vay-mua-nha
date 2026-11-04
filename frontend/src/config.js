// Cấu hình chung. Đổi qua file .env (xem .env.example).
export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const DATA_UPDATED = "2026-10-31"; // ngày cập nhật dữ liệu mặc định
export const FEATURES = { attach: false }; // bật khi backend hỗ trợ tải tài liệu

export const SUGGESTIONS = [
  { icon: "house", text: "Tôi muốn tìm hiểu vay mua nhà" },
  { icon: "calc", text: "Tính khoản vay cho tôi" },
  { icon: "bars", text: "So sánh lãi suất ngân hàng" },
  { icon: "help", text: "Điều kiện để được vay là gì?" },
];
