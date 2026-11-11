# Backend – Chatbot vay mua nhà

Server API viết bằng Python + FastAPI. Hiện tại mọi endpoint chỉ trả dữ liệu mẫu.

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
| `POST /api/chat` | `{"message": "quy trình vay", "session_id": "<uuid>"}` | Câu trả lời mẫu (chưa nối `ai_service`) |
| `POST /api/estimate` | `{"amount": 1500000000, "years": 20}` | Tiền trả tháng đầu (13.017.349 đ) và tổng lãi, tính bằng `finance/calculator.py` |
| `GET /api/banks` | không cần gửi gì | 3 ngân hàng mẫu đọc từ `data/banks_sample.json` |

**Thử:** mở http://127.0.0.1:8000/docs, chọn endpoint, bấm **Try it out** rồi bấm **Execute**.

Backend chạy ở cổng **8000**. `ai_service/` chạy ở cổng 8001 và gọi `POST /api/estimate` của backend để tính khoản vay.

## 3. Chạy test

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Gồm test hàm tính (`tests/test_calculator.py`) và test hợp đồng API (`tests/test_api.py`).
