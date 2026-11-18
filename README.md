# chatbot-vay-mua-nha

Chatbot tư vấn vay mua nhà (đồ án nhóm, IUH). Người dùng hỏi về thủ tục, điều kiện vay, lãi suất và ước tính số tiền phải trả mỗi tháng; câu trả lời dựa trên tài liệu có nguồn, số liệu do công cụ tính toán của backend tính, chỉ mang tính tham khảo.

| Thành phần | Thư mục | Cổng |
|---|---|---|
| Giao diện (React + Vite) | `frontend/` | 5173 |
| Backend (FastAPI): chat, tính khoản vay, dữ liệu ngân hàng | `backend/` | 8000 |
| Dịch vụ AI (FastAPI, LLM + RAG) | `ai_service/` | 8001 |
| Database (PostgreSQL + pgvector, Docker) | `ai_service/docker-compose.yaml` | 5433 |

Hợp đồng API giữa các phần: `docs/api.md`.

## Chạy demo

### Cần cài sẵn
- **Docker Desktop**
- **Python 3.12** và **[uv](https://docs.astral.sh/uv/)**
- **Node.js**
- **Git Bash** (Windows) để chạy script
- Có **Internet**: LLM và embedding được gọi qua mạng

### Cài đặt lần đầu (mỗi máy một lần)
1. Tạo file cấu hình cho dịch vụ AI:
   ```bash
   cp ai_service/.env.example ai_service/.env
   ```
   Điền các giá trị trong `ai_service/.env`: mật khẩu PostgreSQL và `DATABASE_URL`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`, `DATA_ENCRYPTION_KEY_BASE64`. Xin trưởng nhóm các giá trị này. **Không commit file `.env`** (repo công khai).
2. Nạp kho tri thức FAQ (chỉ cần khi database còn trống hoặc khi `data/faq.json` thay đổi). Xem mục "Nạp FAQ" trong `ai_service/README.md`:
   ```bash
   cd ai_service
   docker compose up -d db
   uv run --python 3.12 alembic upgrade head
   docker compose up -d --build worker
   uv run --python 3.12 python scripts/ingest_faq.py --reviewed-by "<tên người duyệt>" --wait
   docker compose stop worker
   ```

### Chạy (mỗi lần demo)
Từ thư mục gốc repo:
```bash
bash scripts/chay-demo.sh
```
Script tự làm lần lượt: mở Docker Desktop nếu chưa chạy → bật database → chạy migration → bật dịch vụ AI → bật backend (đã nối dịch vụ AI) → bật giao diện ở chế độ gọi backend thật → mở trình duyệt tại http://localhost:5173. Lần đầu chạy sẽ tự `npm install` cho giao diện.

Bấm **Ctrl + C** để tắt tất cả. Tùy chọn:
- `--giu-db`: khi tắt vẫn để database chạy, lần sau khởi động nhanh hơn;
- `--khong-mo`: không tự mở trình duyệt.

Log của từng dịch vụ nằm trong `.demo-logs/`.

### Lỗi hay gặp
| Hiện tượng | Nguyên nhân và cách xử lý |
|---|---|
| Script báo cổng 8001, 8000 hoặc 5173 đang bận | Còn demo cũ hoặc chương trình khác đang chạy; tắt nó rồi chạy lại |
| Bot trả "Mình chưa có câu trả lời mẫu cho câu hỏi này..." | Giao diện đang chạy chế độ mock (`npm run dev`), không gọi backend. Dùng script này hoặc `npm run dev:backend` |
| Câu trả lời có chữ "(dữ liệu mẫu)" | Backend chạy thiếu `AI_SERVICE_URL` (script đã đặt sẵn) |
| Thẻ lỗi "Máy chủ chưa trả lời được" (502) | Dịch vụ AI lỗi hoặc máy mất mạng; xem `.demo-logs/ai_service.log` |
| Bot trả "chưa có thông tin" cho mọi câu hỏi | Kho tri thức chưa được nạp FAQ (bước 2 ở trên) |
| Sửa `data/banks_sample.json` mà giao diện vẫn hiện số cũ | Backend giữ dữ liệu trong bộ nhớ; tắt và chạy lại script |

### Chạy riêng từng phần (khi phát triển)
- Backend: `cd backend && pip install -r requirements.txt && AI_SERVICE_URL=http://127.0.0.1:8001 uvicorn app.main:app --reload --port 8000` (không đặt `AI_SERVICE_URL` thì `/api/chat` trả câu mẫu); test: `pip install -r requirements-dev.txt && python -m pytest`
- Dịch vụ AI: `ai_service/README.md`
- Giao diện: `cd frontend && npm run dev` (mock, không cần backend) hoặc `npm run dev:backend`

Thông tin trong chatbot chỉ mang tính tham khảo, vui lòng xác nhận trực tiếp với ngân hàng.
