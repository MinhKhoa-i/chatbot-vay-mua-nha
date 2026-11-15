# Backend – Chatbot vay mua nhà

Server API viết bằng Python + FastAPI. `/api/chat` hỏi `ai_service` khi có đặt `AI_SERVICE_URL`; các endpoint khác dùng dữ liệu mẫu.

## 1. Dựng khung server

**Yêu cầu:** Python 3.10 trở lên.

**Cài đặt** (chỉ làm lần đầu):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Chạy:**

```bash
uvicorn app.main:app --reload --port 8000
```

**Kiểm tra:** mở http://127.0.0.1:8000/api/health. Nếu thấy `{"status":"ok"}` là server đã chạy.

## 2. Endpoint

Hợp đồng đầy đủ (tên trường, lỗi, giá trị cho phép): [docs/api.md](../docs/api.md).

| Endpoint | Gửi lên | Trả về |
|---|---|---|
| `GET /api/health` | không cần gửi gì | `{"status": "ok"}` |
| `POST /api/chat` | `{"message": "quy trình vay", "session_id": "<uuid>"}` | Câu trả lời của `ai_service` và thẻ ước tính `estimate` (xem mục 3, 6); chưa nối thì trả câu mẫu |
| `POST /api/estimate` | `{"amount": 1500000000, "years": 20}` | Tiền trả tháng đầu (13.017.349 đ) và tổng lãi, tính bằng `finance/calculator.py` |
| `GET /api/banks` | không cần gửi gì | Ngân hàng mẫu đọc từ `data/banks_sample.json` |

**Thử:** mở http://127.0.0.1:8000/docs, chọn endpoint, bấm **Try it out** rồi bấm **Execute**.

Backend chạy ở cổng **8000**. `ai_service/` chạy ở cổng 8001 và gọi `POST /api/estimate` của backend để tính khoản vay.

## 3. Nối `/api/chat` với `ai_service`

**Chạy** (bật `ai_service` ở cổng 8001 trước):

```bash
$env:AI_SERVICE_URL="http://127.0.0.1:8001"
uvicorn app.main:app --reload --port 8000
```

**Kiểm tra:** gửi `POST /api/chat` ở trang `/docs`. Nhận câu trả lời do AI viết là đã nối được.

- Không đặt `AI_SERVICE_URL` thì `/api/chat` trả câu mẫu như cũ.
- `ai_service` bận hoặc lỗi thì backend tự thử lại tối đa 3 lần; vẫn lỗi thì trả `502` kèm câu tiếng Việt.
- `AI_SERVICE_TIMEOUT` (không bắt buộc, mặc định 60): số giây chờ mỗi lần gọi.

## 4. Chạy test

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Gồm test hàm tính (`tests/test_calculator.py`) và test hợp đồng API (`tests/test_api.py`). Test `/api/chat` dùng `ai_service` giả, không cần chạy `ai_service` thật.

## 5. /api/estimate trả thêm hạn mức vay tối đa

- Nhận thêm (không bắt buộc): `property_value`, `monthly_income`, `existing_monthly_debt`, `max_ltv_percent` (mặc định 80, theo %: 70 = 70%), `max_dti_percent` (mặc định 50)
- Gửi đủ giá trị nhà + thu nhập thì gọi `max_loan()` của `finance/calculator.py`, trả thêm trường `max_loan` {max_loan, by_ltv, by_dti, limited_by, ...}; không gửi thì `max_loan = null`
- Chỉ gửi một trong hai thì trả 422 kèm câu tiếng Việt
- Cập nhật docs/api.md mục 3.3 và tests/test_api.py

## 6. /api/chat trả thẻ ước tính `estimate` (STT 18)

Khi khách nhờ tính khoản vay trong khung chat, `ai_service` gửi kết quả trong trường `estimate` của event `done`. Backend chuyển tiếp trường này cho frontend để hiện thẻ ước tính.

- `ai_service` có trả `estimate` thì `/api/chat` trả lại đúng `estimate` đó (cùng cấu trúc với response `/api/estimate`: `amount`, `years`, `rate`, `method`, `promo_rate`, `promo_duration_months`, `monthly_payment`, `total_interest`, `updated_at`).
- Câu hỏi không cần tính tiền (ví dụ hỏi hồ sơ vay) thì `estimate = null`.
- Thiếu `monthly_payment` hoặc `total_interest` thì backend tự tính bằng `finance/calculator.py`.
- Dữ liệu `estimate` sai (thiếu số tiền, số âm, sai kiểu...) thì trả `estimate = null` nhưng vẫn trả câu trả lời `reply`, khung chat không bị lỗi.
- `updated_at` của response lấy theo `estimate.updated_at` nếu có.
- Cập nhật docs/api.md mục 3.2, mục 5 và tests/test_api.py (6 ca test mới, tổng 91 passed).

Ví dụ response:

```json
{
  "reply": "Khoản vay 1 tỷ đồng trong 20 năm, lãi suất 9.5%/năm...",
  "updated_at": "2026-11-11",
  "estimate": {
    "amount": 1000000000, "years": 20, "rate": 9.5, "method": "annuity",
    "promo_rate": null, "promo_duration_months": 0,
    "monthly_payment": 9321347, "total_interest": 1237123280,
    "updated_at": "2026-11-11"
  }
}
```
