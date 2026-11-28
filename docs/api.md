# Tài liệu API

Hợp đồng chung giữa Frontend, Backend, AI service, Tài chính và Dữ liệu. Chốt ở tuần 1 (STT 2, STT 16 trong bảng phân công).

- Phiên bản: `0.1.0`, ngày chốt: 2026-11-08
- Ai đổi tên trường, endpoint hay giá trị cho phép thì sửa file này và `backend/tests/test_api.py` **trong cùng PR**, rồi báo cả nhóm.

## 1. Các phần và cổng chạy

```
Trình duyệt ──► frontend (Vite, :5173)
                  │  POST /api/chat, GET /api/banks, POST /api/banks/rank
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

`estimate` gồm đúng các trường `amount`, `years`, `rate`, `method`, `promo_rate`, `promo_duration_months`, `monthly_payment`, `total_interest`, `updated_at` (cùng ý nghĩa với response của `/api/estimate`, mục 3.3). Backend lấy từ event `done` của `ai_service` và kiểm tra trước khi trả (mục 5), nên khi `estimate` khác `null` thì luôn có đủ `monthly_payment` và `total_interest` là số nguyên ≥ 0. Frontend không tự tính khi chạy với backend thật.

**Hiện trạng:** đã đặt biến môi trường `AI_SERVICE_URL` thì backend hỏi `ai_service` theo mục 5 và trả `estimate` lấy từ event `done`; chưa đặt thì trả một câu cố định (dữ liệu mẫu), `estimate: null`.

Lỗi riêng của endpoint này: `ai_service` lỗi, không kết nối được hoặc thử lại hết số lần thì trả **`502`** với `detail` là một câu tiếng Việt. Frontend hiện câu báo lỗi chung.

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
| `grace_period_months` | integer | Không | `0` | Từ 0 đến `years * 12 - 1`. Số tháng đầu chỉ trả lãi (ân hạn nợ gốc), nằm **trong** kỳ hạn |

`promo_rate` và `promo_duration_months` phải đi cùng nhau: có cái này thì phải có cái kia, nếu không sẽ bị lỗi 422.

LTV và hạn mức vay tối đa (không bắt buộc). Gửi `property_value` thì backend trả thêm `ltv_percent`. Gửi **cả** `property_value` và `monthly_income` thì tính thêm `max_loan` bằng `max_loan()` của `calculator.py`, dùng cùng `years`, `rate`, `method`, `promo_rate`, `promo_duration_months`, `grace_period_months` ở trên. Gửi `monthly_income` mà thiếu `property_value` thì lỗi 422.

| Trường | Kiểu | Bắt buộc | Mặc định | Ràng buộc |
|---|---|---|---|---|
| `property_value` | integer | Không | `null` | > 0, giá trị nhà / tài sản bảo đảm (VND) |
| `monthly_income` | integer | Không | `null` | > 0, thu nhập ròng hằng tháng (VND) |
| `existing_monthly_debt` | integer | Không | `0` | ≥ 0, nợ khác đang trả hằng tháng (VND) |
| `max_ltv_percent` | number | Không | `80` | [1, 100], theo % (70 = 70%). Form gửi `loan_limit.max_ltv_percent` của ngân hàng đã chọn |
| `max_dti_percent` | number | Không | `50` | (0, 100] |

Phí trả nợ trước hạn (không bắt buộc). Gửi **cả** hai trường thì backend tính thêm `prepay` bằng `prepay_fee()` của `calculator.py`. Chỉ gửi một trong hai thì lỗi 422 với `detail` = "Cần nhập cả số tiền trả trước và tỷ lệ phí trả trước hạn".

| Trường | Kiểu | Bắt buộc | Mặc định | Ràng buộc |
|---|---|---|---|---|
| `prepay_amount` | integer | Không | `null` | > 0, ≤ `amount`, số gốc định trả trước (VND) |
| `prepay_fee_percent` | number | Không | `null` | [0, 100], tỷ lệ phí theo hợp đồng (%) |

Trường số nguyên không nhận `true`/`false`; trường số thực không nhận `NaN`/`Infinity`. Gửi sai thì lỗi 422.

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
  "grace_period_months": 0,
  "monthly_payment": 13017349,
  "max_monthly_payment": 13017349,
  "max_payment_month": 1,
  "grace_monthly_payment": null,
  "after_grace_monthly_payment": null,
  "total_interest": 1624163639,
  "max_loan": null,
  "ltv_percent": null,
  "prepay": null,
  "updated_at": "2026-10-31"
}
```

Khi gửi thêm `"property_value": 3000000000, "monthly_income": 40000000, "max_ltv_percent": 70`, trường `max_loan` có dạng:

```json
"max_loan": {
  "max_loan": 2100000000,
  "by_ltv": 2100000000,
  "by_dti": 2304616796,
  "limited_by": "ltv",
  "max_ltv_percent": 70.0,
  "max_dti_percent": 50.0
}
```

và `"ltv_percent": 50.0` (1,5 tỷ / 3 tỷ). Khi gửi thêm `"prepay_amount": 200000000, "prepay_fee_percent": 1`:

```json
"prepay": { "amount": 200000000, "fee_percent": 1.0, "fee": 2000000 }
```

| Trường | Ghi chú |
|---|---|
| `amount`, `years`, `rate`, `method`, `promo_rate`, `promo_duration_months`, `grace_period_months` | Trả lại đúng giá trị đã gửi. `ai_service` dùng các trường này để kiểm tra response có đúng là của request mình gửi không |
| `monthly_payment` | Tiền trả **tháng đầu tiên**, VND, số nguyên. Niên kim: số tiền đều hằng tháng (trong thời gian ưu đãi). Gốc đều không ưu đãi: tháng cao nhất. Tháng cao nhất xem `max_monthly_payment` |
| `max_monthly_payment` | Tiền trả của tháng **cao nhất** trong cả kỳ hạn, VND, số nguyên (= `max(payment)` của `schedule()`). Có ưu đãi thì tháng đầu chưa chắc cao nhất: gốc đều vay 2 tỷ, 20 năm, ưu đãi 9% 12 tháng rồi 10% thì tháng 1 là 23.333.333 đ, tháng 13 là 24.166.667 đ. Form dùng số này cho tỷ lệ trả nợ / thu nhập và cảnh báo 50% (bug #81, FORM-15), khớp với `by_dti` của `max_loan` |
| `max_payment_month` | Tháng có `max_monthly_payment` (bắt đầu từ 1). Nhiều tháng bằng nhau thì lấy tháng sớm nhất |
| `grace_monthly_payment` | `null` nếu `grace_period_months` = 0. Nếu có: tiền trả mỗi tháng ân hạn (chỉ có lãi, tháng 1), VND |
| `after_grace_monthly_payment` | `null` nếu `grace_period_months` = 0. Nếu có: tiền trả tháng đầu sau ân hạn (tháng `grace_period_months + 1`), VND. Ví dụ EVAL-47 (1,2 tỷ, 20 năm, 9%, gốc đều, ân hạn 12 tháng): ân hạn 9.000.000 đ, tháng 13 là 14.263.158 đ (1,2 tỷ / 228 tháng + lãi 9 triệu). Issue #87 |
| `total_interest` | Tổng lãi cả kỳ hạn, VND, số nguyên |
| `max_loan` | `null` nếu không gửi `property_value` và `monthly_income`. Nếu có: `max_loan` = hạn mức tối đa (VND) = min(`by_ltv`, `by_dti`); `by_ltv` = theo giá trị nhà; `by_dti` = theo thu nhập (tính với tháng phải trả **cao nhất**); `limited_by` = `"ltv"` hoặc `"dti"` cho biết bị giới hạn bởi cái nào; kèm hai tỷ lệ đã dùng |
| `ltv_percent` | `null` nếu không gửi `property_value`. Nếu có: `ltv(amount, property_value) * 100` (hàm `ltv()` trả tỷ lệ 0,5 = 50%), làm tròn 2 chữ số thập phân. Dùng cho EVAL-06 |
| `prepay` | `null` nếu không gửi `prepay_amount` và `prepay_fee_percent`. Nếu có: `amount` = số gốc trả trước, `fee_percent` = tỷ lệ phí, `fee` = phí (VND, số nguyên) từ `prepay_fee()`. Dùng cho EVAL-22 |
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

### 3.5. `POST /api/banks/rank`

Xếp hạng các gói vay trong `data/banks_sample.json` từ rẻ đến đắt theo **tổng chi phí = tiền lãi + phí trả nợ trước hạn**, bằng `rank_banks()` của `backend/finance/ranking.py`. Thứ tự chỉ để so sánh, không phải khuyến nghị.

Gửi lên:

| Trường | Kiểu | Bắt buộc | Mặc định | Ràng buộc |
|---|---|---|---|---|
| `amount` | integer | Có | | > 0, VND |
| `years` | integer | Có | | 1–35 |
| `method` | string | Không | `"annuity"` | `"annuity"` hoặc `"reducing_balance"` |
| `grace_period_months` | integer | Không | `0` | ≥ 0 và nhỏ hơn `years * 12`. Số tháng đầu chỉ trả lãi |
| `prepay_month` | integer | Không | `null` | 1 đến `years * 12 - 1`. Trả hết nợ sau bấy nhiêu tháng; `null` = giữ đến hết kỳ hạn |
| `property_value` | integer | Không | `null` | > 0. Có thì loại ngân hàng có LTV tối đa thấp hơn mức cần vay |
| `base_rate` | number | Không | `null` | ≥ 0, lãi cơ sở %/năm, cộng với `floating_margin` của ngân hàng |
| `assumed_floating_rate` | number | Không | `null` | ≥ 0, lãi thả nổi **giả định** %/năm cho ngân hàng không công bố lãi thả nổi |

Dữ liệu mẫu hiện chưa có lãi thả nổi (`floating_rate_estimated`, `floating_margin` đều `null`). Không gửi `base_rate` hoặc `assumed_floating_rate` thì các ngân hàng cần lãi thả nổi bị đưa vào `excluded`. Frontend nên gửi `assumed_floating_rate` và hiện rõ đó là giả định.

Ví dụ: `{ "amount": 1500000000, "years": 20, "prepay_month": 36, "assumed_floating_rate": 10 }`

Trả về:

```json
{
  "ranked": [
    {
      "id": "agribank",
      "short_name": "Agribank",
      "package_name": "Vay mua nhà ở thương mại",
      "total_cost": 466928374,
      "total_interest": 438579027,
      "prepay_fee": 28349347,
      "prepay_fee_known": true,
      "prepay_fee_is_upper_bound": false,
      "first_payment": 14475325,
      "floating_rate": 10.0,
      "floating_rate_assumed": true
    }
  ],
  "excluded": [],
  "assumptions": { "floating_rate": 10.0 },
  "updated_at": "2026-11-16",
  "is_sample": true
}
```

| Trường | Ghi chú |
|---|---|
| `ranked` | Ngân hàng phù hợp, từ rẻ đến đắt. Ngân hàng chưa rõ phí trả trước (`total_cost: null`) xếp sau, theo `total_interest` |
| `total_cost` | Tiền lãi + phí trả trước (VND). `null` nếu phí trả trước chưa rõ |
| `total_interest` | Tiền lãi đến tháng trả hết nợ (hoặc cả kỳ hạn) |
| `prepay_fee` | Phí trả trước (VND); `0` khi không trả trước; `null` nếu chưa rõ. `prepay_fee_is_upper_bound: true` = đây là mức tối đa |
| `first_payment` | Tiền trả tháng đầu (VND) |
| `floating_rate`, `floating_rate_assumed` | Lãi thả nổi đã dùng; `true` = lấy từ `assumed_floating_rate`, giao diện phải ghi là giả định |
| `excluded` | Ngân hàng không phù hợp (thời hạn, số tiền, phương thức, ân hạn, LTV, thiếu lãi thả nổi) kèm `reason` tiếng Việt |
| `assumptions` | `{"floating_rate": ...}` nếu có ngân hàng dùng lãi giả định, ngược lại `{}` |

Lỗi: sai kiểu hoặc ngoài khoảng → `422` danh sách lỗi; `ranking.py` từ chối (ví dụ `prepay_month` ≥ số tháng vay, ân hạn ≥ số tháng vay) → `422` với `detail` là một câu tiếng Việt.

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

`ai_service` gọi `POST {LOAN_BACKEND_BASE_URL}/api/estimate` khi khách nhờ tính khoản vay. `LOAN_BACKEND_BASE_URL` đặt trong `ai_service/.env`, mặc định `http://127.0.0.1:8000`. Bot hỏi đủ số tiền vay, thời hạn, phương thức trả nợ (`annuity` hoặc `reducing_balance`), có lãi ưu đãi hay không (nếu có: `promo_rate` và `promo_duration_months`) và lãi suất (`rate`; có ưu đãi thì là lãi sau ưu đãi). Khách xác nhận xong, bot gửi đủ `amount`, `years`, `rate`, `method`, `promo_rate`, `promo_duration_months`, rồi kiểm tra response trả lại đúng các giá trị này. Chưa hỗ trợ ân hạn nợ gốc, trả trước, phí và hạn mức vay qua chat.

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

`estimate` dùng cùng cấu trúc phẳng với response `POST /api/estimate` (mục 3.3): đầu vào gồm `amount`, `years`, `rate`, `method`, `promo_rate`, `promo_duration_months`; kết quả gồm `monthly_payment`, `total_interest`, `updated_at`. `rate` là số. `method`, `promo_rate`, `promo_duration_months` là đúng giá trị khách đã xác nhận; không có ưu đãi thì `promo_rate` là `null` và `promo_duration_months` là `0`. Khi lượt chat không tạo kết quả estimate, trường này là `null`.

## 5. Nối backend với AI service

Mục tiêu: frontend **không đổi** gì, vẫn gọi `POST /api/chat`. Code nằm trong `backend/app/main.py` (phần "Nối /api/chat với ai_service").

1. Backend nhận `{ message, session_id }`.
2. Backend gọi `POST {AI_SERVICE_URL}/api/v1/conversations/{conversation_id}/messages` với `{ "client_request_id": <uuid v4 mới>, "text": message }`.
   - `conversation_id` = `session_id` nếu đó là UUID (frontend dùng `crypto.randomUUID()`). Nếu `session_id` là chuỗi khác thì backend đổi thành một UUID cố định theo chuỗi đó (uuid5), nên cùng `session_id` vẫn cùng cuộc trò chuyện. Không gửi `session_id` thì mỗi tin nhắn là một cuộc trò chuyện mới.
3. Backend đọc SSE đến event `done`, lấy `reply` và `estimate`, rồi trả `{ reply, updated_at, estimate }` cho frontend. Event `delta` bị bỏ qua.
   - `estimate`: backend kiểm tra các trường đầu vào (`amount`, `years`, `rate`, ...) bằng cùng quy tắc của `/api/estimate`. `monthly_payment`, `total_interest` phải là số nguyên ≥ 0; thiếu hoặc sai (số âm, số lẻ, chuỗi) thì backend tự tính lại bằng `calculator.py`. Đầu vào sai thì trả `estimate: null` nhưng vẫn trả `reply`. Trường lạ không có trong hợp đồng bị bỏ.
   - `updated_at` của response lấy theo `estimate.updated_at` nếu có, không thì là ngày dữ liệu của backend.
4. Thử lại tối đa **3 lần** (tính cả lần đầu) với **cùng** `client_request_id` khi: event `error` có `retryable: true` (chờ `retry_after` giây nếu có), lỗi mạng, hết giờ, HTTP 5xx, hoặc luồng kết thúc mà không có `done`. Lỗi `retryable: false` hoặc HTTP 4xx thì dừng ngay. Hết số lần thì backend trả `502`.
5. Chưa đặt `AI_SERVICE_URL` thì backend giữ câu trả lời mẫu.

Biến môi trường của backend:

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `AI_SERVICE_URL` | (trống) | Ví dụ `http://127.0.0.1:8001`. Để trống thì dùng câu trả lời mẫu |
| `AI_SERVICE_TIMEOUT` | `60` | Số giây chờ `ai_service` trả lời mỗi lần gửi |

Còn mở: có cho frontend nhận chữ chạy dần (stream) không. Nếu có thì thêm endpoint `POST /api/chat/stream` riêng, giữ `POST /api/chat` như cũ.

## 6. Bảng tên trường dùng chung

| Ý nghĩa | `data/` + `docs/schema.md` | `calculator.py` | `/api/estimate` | Frontend | `ai_service` |
|---|---|---|---|---|---|
| Số tiền vay | `min_loan_amount`, `max_loan_amount` (hạn mức) | `principal` | `amount` | `estimate.amount` | `amount` |
| Thời hạn | `max_loan_term_years` | `months` | `years` | `estimate.years` | `years` |
| Lãi ưu đãi | `interest_rate.promo_rate` | `promo_rate` | `promo_rate` | | `promo_rate` |
| Số tháng ưu đãi | `interest_rate.promo_duration_months` | `promo_duration_months` | `promo_duration_months` | | `promo_duration_months` |
| Lãi sau ưu đãi | `floating_rate_estimated` hoặc lãi cơ sở + `floating_margin` | `annual_rate` | `rate` | `estimate.rate` | `rate` |
| Phương thức | `repayment_methods[]` | `method` | `method` | `estimate.method` | `method` |
| Tỷ lệ cho vay | `max_ltv_percent` (đơn vị %, 70 = 70%) | max_loan() nhận `max_ltv` theo % (80) còn `max_dti` theo tỷ lệ (0.5) | | | |
| Ngày cập nhật | `updated_at` (file), `last_updated` (từng gói) | | `updated_at` | `updated_at` | `updated_at` |

Lưu ý: `max_ltv_percent` tính theo **%** (70), còn `ltv()` trả về **tỷ lệ** (0.7). So sánh hai giá trị thì nhân hoặc chia cho 100.

## 7. Việc còn mở
- Chế độ mock của frontend tính bằng `schedule()` trong `frontend/src/lib/loan.js`, bản chép của `calculator.py`. Sửa công thức hay câu báo lỗi ở `calculator.py` thì sửa cả bản JS (Định, Sang).
- `DATA_UPDATED` đang khai báo hai nơi (`backend/app/main.py`, `frontend/src/config.js`). Đổi ngày thì sửa cả hai.

