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

## 2. Endpoint giả (dữ liệu mẫu)

| Endpoint| Gửi lên | Trả về |
|------------------|---------|--------|
| `POST /api/chat` | `{"message": "quy trình vay", "session_id": "1"}` | Câu trả lời mẫu |
| `POST /api/estimate` | `{"amount": 1500000000, "years": 20}` | Tiền trả hằng tháng (13.017.349 đ) |
| `GET /api/banks` | không cần gửi gì | 3 ngân hàng mẫu |

**Thử:** mở http://127.0.0.1:8000/docs, chọn endpoint, bấm **Try it out** rồi bấm **Execute**.
