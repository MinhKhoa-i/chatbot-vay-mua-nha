# Tài liệu API

Hợp đồng chung giữa Frontend, Backend, AI service, Tài chính và Dữ liệu. Chốt ở tuần 1 (STT 2, STT 16 trong bảng phân công).

- Phiên bản: `0.1.0`, ngày chốt: 2026-11-08
- Ai đổi tên trường, endpoint hay giá trị cho phép thì sửa file này và `backend/tests/test_api.py` **trong cùng PR**, rồi báo cả nhóm.

## 1. Các phần và cổng chạy

```
Trình duyệt ──► frontend (Vite, :5173)
                  │  POST /api/chat, GET /api/banks
                  ▼
              backend (FastAPI, :8000)  ◄──── POST /api/estimate ──── ai_service (FastAPI, :8001)
                  │                                                     │
                  └── backend/finance/calculator.py                     └── PostgreSQL + pgvector (:5432)
                  └── data/banks_sample.json
```

| Phần | Thư mục | Cổng | Ai phụ trách |
|---|---|---|---|
| Frontend | `frontend/` | 5173 | Sang |
| Backend | `backend/` | **8000** | Hiếu |
| Hàm tính khoản vay | `backend/finance/calculator.py` | (thư viện, không có cổng) | Định |
| AI service (RAG, chat) | `ai_service/` | **8001** | Hoàn |
| Dữ liệu ngân hàng | `data/banks_sample.json`, `docs/schema.md` | | Vương |

Quy tắc:
- **Frontend chỉ gọi backend** (`VITE_API_URL=http://localhost:8000`). Frontend không gọi thẳng `ai_service`.
- **Mọi phép tính tiền đều qua `calculator.py`.** Backend gọi hàm này; `ai_service` gọi `POST /api/estimate` của backend. LLM không được tự tính số.
- CORS của backend cho phép `localhost` và `127.0.0.1` ở cổng 5173, 5174. Đổi cổng dev thì sửa danh sách trong `backend/app/main.py`.

## 2. Quy ước chung

| Nội dung | Quy ước | Ví dụ |
|---|---|---|
| Định dạng | JSON, UTF-8 | |
| Tiền | VND, **số nguyên** | `1500000000` |
| Lãi suất | **%/năm**, số thực (không dùng dạng thập phân 0,085) | `8.5` |
| Thời hạn vay | `years` (số nguyên năm, 1–35) ở API; `calculator.py` dùng số tháng = `years * 12` | `20` |
| Thời gian ưu đãi | `promo_duration_months` (số nguyên tháng) | `12` |
| Phương thức trả nợ | `"annuity"` (niên kim, trả đều gốc + lãi) hoặc `"reducing_balance"` (gốc đều, lãi giảm dần) | |
| Ngày | `YYYY-MM-DD` | `"2026-10-31"` |
| Ngày cập nhật dữ liệu | Mọi response có `updated_at`; giao diện phải hiển thị ngày này | |
| Mã phiên chat | UUID v4 do frontend tạo (`crypto.randomUUID()`) | `"2dd4d22a-993d-4a2e-b544-91409ebfb17b"` |

**Lỗi.** Backend dùng mã HTTP chuẩn của FastAPI:
- `422`: dữ liệu gửi lên sai. Nếu sai kiểu hoặc thiếu trường, `detail` là **danh sách** lỗi của FastAPI. Nếu `calculator.py` từ chối (ví dụ ưu đãi dài hơn kỳ hạn), `detail` là **một câu tiếng Việt**: `{"detail": "Số tháng ưu đãi không được lớn hơn số tháng vay"}`.
- `500`: lỗi máy chủ. Frontend hiển thị câu báo lỗi chung, không hiện chi tiết kỹ thuật.

## 3. Backend (`http://localhost:8000`)

Swagger: http://localhost:8000/docs

### 3.1. `GET /api/health`

Trả về `{"status": "ok"}`.

### 3.2. `POST /api/chat`

Gửi lên:

| Trường | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `message` | string | Có | 1–1000 ký tự |
| `session_id` | string | Không | UUID v4 của cuộc trò chuyện |

Trả về:

```json
{
  "reply": "Quy trình vay mua nhà gồm 5 giai đoạn: ...",
  "updated_at": "2026-10-31",
  "estimate": null
}
```

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `reply` | string | Văn bản trả lời, có thể có xuống dòng |
| `updated_at` | string | Ngày cập nhật dữ liệu dùng để trả lời |
| `estimate` | object hoặc `null` | Có khi câu trả lời kèm ước tính khoản vay; frontend hiển thị thẻ ước tính |

`estimate` có cùng các trường với response của `/api/estimate` (mục 3.3). Bắt buộc có `amount`, `years`, `rate`; nên có thêm `method`, `monthly_payment`, `total_interest`. Nếu thiếu `monthly_payment` hoặc `total_interest`, thẻ ước tính của frontend gọi `POST /api/estimate` với `amount`, `years`, `rate`, `method`, `promo_rate`, `promo_duration_months` để lấy số; frontend không tự tính khi chạy với backend thật.

**Hiện trạng:** backend trả một câu cố định (dữ liệu mẫu). Kế hoạch nối với `ai_service` ở mục 5.

### 3.3. `POST /api/estimate`

Tính khoản trả hàng tháng bằng `backend/finance/calculator.py`.

Gửi lên:

| Trường | Kiểu | Bắt buộc | Mặc định | Ràng buộc |
|---|---|---|---|---|
| `amount` | integer | Có | | > 0, VND |
| `years` | integer | Có | | 1–35 |
| `rate` | number | Không | `8.5` | ≥ 0. Nếu có ưu đãi thì đây là lãi **sau** ưu đãi (thả nổi) |
| `method` | string | Không | `"annuity"` | `"annuity"` hoặc `"reducing_balance"` |
| `promo_rate` | number | Không | `null` | ≥ 0, lãi ưu đãi %/năm |
| `promo_duration_months` | integer | Không | `0` | ≥ 0, không vượt quá `years * 12` |

`promo_rate` và `promo_duration_months` phải đi cùng nhau: có cái này thì phải có cái kia, nếu không sẽ bị lỗi 422.

Ví dụ:

```json
{ "amount": 1500000000, "years": 20 }
```

Trả về:

```json
{
  "amount": 1500000000,
  "years": 20,
  "rate": 8.5,
  "method": "annuity",
  "promo_rate": null,
  "promo_duration_months": 0,
  "monthly_payment": 13017349,
  "total_interest": 1624163639,
  "updated_at": "2026-10-31"
}
```

| Trường | Ghi chú |
|---|---|
| `amount`, `years`, `rate`, `method`, `promo_rate`, `promo_duration_months` | Trả lại đúng giá trị đã gửi. `ai_service` dùng các trường này để kiểm tra response có đúng là của request mình gửi không |
| `monthly_payment` | Tiền trả **tháng đầu tiên**, VND, số nguyên. Niên kim: số tiền đều hằng tháng (trong thời gian ưu đãi). Gốc đều: tháng cao nhất |
| `total_interest` | Tổng lãi cả kỳ hạn, VND, số nguyên |
| `updated_at` | Ngày cập nhật dữ liệu |

Làm tròn đến đồng; phần chênh do làm tròn dồn vào tháng cuối nên tổng tiền gốc luôn bằng `amount`.

Form nhập thông tin khách ở frontend (STT 18) gọi endpoint này và `GET /api/banks`. Khi khách chọn ngân hàng, form gửi `rate` = `floating_rate_estimated`, `promo_rate` và `promo_duration_months` lấy từ `interest_rate` của gói vay. Tỷ lệ vay/giá trị nhà và trả nợ/thu nhập chỉ là phép chia trên giao diện, dùng `monthly_payment` do backend trả về.

### 3.4. `GET /api/banks`

Trả về dữ liệu mẫu đọc từ `data/banks_sample.json`. Mỗi phần tử của `banks` là một gói vay theo đúng `docs/schema.md`, backend không đổi tên trường.

```json
{
  "banks": [
    {
      "id": "vietcombank",
      "short_name": "Vietcombank",
      "interest_rate": { "promo_rate": 5.2, "promo_duration_months": 12, "floating_margin": 3.5, "...": "..." },
      "loan_limit": { "max_ltv_percent": 70.0, "max_loan_term_years": 30, "...": "..." },
      "repayment_methods": ["reducing_balance", "annuity"],
      "last_updated": "2026-10-31",
      "disclaimer": "Thông tin chỉ mang tính tham khảo...",
      "...": "..."
    }
  ],
  "updated_at": "2026-10-31",
  "is_sample": true
}
```

`is_sample: true` nghĩa là dữ liệu nhập tay, chưa phải dữ liệu crawl. Giao diện phải hiện `last_updated` của từng ngân hàng và câu `disclaimer`.

## 4. AI service (`http://localhost:8001`)

Chi tiết nằm trong `ai_service/docs/chat-streaming-api.md` và `ai_service/docs/conversation-api.md`. Tóm tắt:

| Endpoint | Việc |
|---|---|
| `GET /health` | Kiểm tra service |
| `POST /api/v1/conversations` | Tạo cuộc trò chuyện (không bắt buộc, gửi tin nhắn đầu sẽ tự tạo) |
| `GET /api/v1/conversations/{conversation_id}` | Xem trạng thái |
| `GET /api/v1/conversations/{conversation_id}/messages` | Lịch sử tin nhắn |
| `DELETE /api/v1/conversations/{conversation_id}` | Xóa cuộc trò chuyện |
| `POST /api/v1/conversations/{conversation_id}/messages` | Gửi tin nhắn, trả về SSE (`delta`, `done`, `error`) |
| `POST /api/v1/knowledge/documents` | Tải tài liệu vào kho tri thức (multipart) |
| `GET /api/v1/knowledge/documents/{document_id}` | Trạng thái xử lý tài liệu |

Gửi tin nhắn:

```json
{ "client_request_id": "<uuid v4, mỗi tin nhắn một mã>", "text": "Hồ sơ vay mua nhà gồm gì?" }
```

`ai_service` gọi `POST {LOAN_BACKEND_BASE_URL}/api/estimate` khi khách nhờ tính khoản vay. `LOAN_BACKEND_BASE_URL` đặt trong `ai_service/.env`, mặc định `http://127.0.0.1:8000`. Hiện bot chỉ gửi `amount`, `years`, `rate` (niên kim, lãi cố định) và kiểm tra response có `method == "annuity"`.

Event SSE `done` chứa `estimate` có cấu trúc khi lượt chat hoàn tất phép tính thành công; nếu lượt chat không tạo estimate thì trường này là `null`. Ví dụ phần `data` của event:

```json
{
  "reply": "Khoản vay 1 tỷ đồng trong 20 năm, lãi suất 9.5%/năm...",
  "estimate": {
    "amount": 1000000000,
    "years": 20,
    "rate": 9.5,
    "method": "annuity",
    "promo_rate": null,
    "promo_duration_months": 0,
    "monthly_payment": 8770000,
    "total_interest": 1104800000,
    "updated_at": "2026-10-31"
  }
}
```

`estimate` dùng cùng cấu trúc phẳng với response `POST /api/estimate` (mục 3.3): đầu vào gồm `amount`, `years`, `rate`, `method`, `promo_rate`, `promo_duration_months`; kết quả gồm `monthly_payment`, `total_interest`, `updated_at`. `rate` là số. Vì `ai_service` hiện chỉ hỗ trợ niên kim lãi cố định, `method` luôn là `"annuity"`, `promo_rate` là `null` và `promo_duration_months` là `0`. Khi lượt chat không tạo kết quả estimate, trường này là `null`.

## 5. Nối backend với AI service (việc của tuần 2)

Mục tiêu: frontend **không đổi** gì, vẫn gọi `POST /api/chat`.

1. Backend nhận `{ message, session_id }`.
2. Backend gọi `POST {AI_SERVICE_URL}/api/v1/conversations/{session_id}/messages` với `{ "client_request_id": <uuid mới>, "text": message }`.
3. Backend đọc SSE đến event `done`, lấy `reply`, rồi trả `{ reply, updated_at, estimate }` cho frontend. Gặp event `error` có `retryable: true` thì thử lại với **cùng** `client_request_id`.
4. Chưa đặt `AI_SERVICE_URL` thì backend giữ câu trả lời mẫu như hiện nay.

Cần chốt khi làm: có cho frontend nhận chữ chạy dần (stream) không. Nếu có thì thêm endpoint `POST /api/chat/stream` riêng, giữ `POST /api/chat` như cũ. Event `done` đã trả `estimate` có cấu trúc như mô tả ở trên; backend có thể dùng trường này để cung cấp thẻ ước tính cho frontend khi nối hai service.

## 6. Bảng tên trường dùng chung

| Ý nghĩa | `data/` + `docs/schema.md` | `calculator.py` | `/api/estimate` | Frontend | `ai_service` |
|---|---|---|---|---|---|
| Số tiền vay | `min_loan_amount`, `max_loan_amount` (hạn mức) | `principal` | `amount` | `estimate.amount` | `amount` |
| Thời hạn | `max_loan_term_years` | `months` | `years` | `estimate.years` | `years` |
| Lãi ưu đãi | `interest_rate.promo_rate` | `promo_rate` | `promo_rate` | | |
| Số tháng ưu đãi | `interest_rate.promo_duration_months` | `promo_duration_months` | `promo_duration_months` | | |
| Lãi sau ưu đãi | `floating_rate_estimated` hoặc lãi cơ sở + `floating_margin` | `annual_rate` | `rate` | `estimate.rate` | `rate` |
| Phương thức | `repayment_methods[]` | `method` | `method` | `estimate.method` | `"annuity"` |
| Tỷ lệ cho vay | `max_ltv_percent` (đơn vị %, 70 = 70%) | `ltv()` trả tỷ lệ (0.7 = 70%) | | | |
| Ngày cập nhật | `updated_at` (file), `last_updated` (từng gói) | | `updated_at` | `updated_at` | `updated_at` |

Lưu ý: `max_ltv_percent` tính theo **%** (70), còn `ltv()` trả về **tỷ lệ** (0.7). So sánh hai giá trị thì nhân hoặc chia cho 100.

## 7. Việc còn mở

- Nối `/api/chat` với `ai_service` theo mục 5 (Hiếu và Hoàn).
- Cho bot hỏi phương thức trả nợ và ưu đãi rồi gửi `method`, `promo_rate`, `promo_duration_months`, vì backend đã hỗ trợ (Hoàn).
- Ân hạn nợ gốc (`grace_period_months`) chưa có trong `calculator.py` (Định).
- Chế độ mock của frontend tính bằng `schedule()` trong `frontend/src/lib/loan.js`, bản chép của `calculator.py`. Sửa công thức hay câu báo lỗi ở `calculator.py` thì sửa cả bản JS (Định, Sang).
- `DATA_UPDATED` đang khai báo hai nơi (`backend/app/main.py`, `frontend/src/config.js`). Đổi ngày thì sửa cả hai.
