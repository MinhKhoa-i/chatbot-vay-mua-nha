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
| `POST /api/chat` | `{"message": "quy trình vay", "session_id": "<uuid>"}` | Câu trả lời của `ai_service` (xem mục 3); chưa nối thì trả câu mẫu |
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

## 5. /api/estimate trả thêm hạn mức vay tối đa
Gồm test hàm tính (`tests/test_calculator.py`) và test hợp đồng API (`tests/test_api.py`). Test `/api/chat` dùng `ai_service` giả, không cần chạy `ai_service` thật.
- Nhận thêm (không bắt buộc): property_value, monthly_income, existing_monthly_debt, max_ltv_percent (mặc định 80), max_dti_percent (mặc định 50)
- Gửi đủ giá trị nhà + thu nhập thì gọi max_loan() của finance/calculator.py, trả thêm trường max_loan {max_loan, by_ltv, by_dti, limited_by, ...}; không gửi thì max_loan = null
- Chỉ gửi một trong hai thì trả 422 kèm câu tiếng Việt
- Cập nhật docs/api.md mục 3.3 và tests/test_api.py (27 passed)

Dựa trên PR việc 16 (feature/chat-ai-service), nhờ merge PR 16 trước.
