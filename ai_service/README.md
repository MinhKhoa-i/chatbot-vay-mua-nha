# AI Service — hướng dẫn chạy demo cục bộ

Hướng dẫn này dành cho môi trường demo phát triển, không phải cấu hình triển khai production. AI service là ứng dụng riêng trong `ai_service/`, dùng PostgreSQL + pgvector, một worker xử lý ingestion, dịch vụ embedding tương thích OpenAI và dịch vụ chat tương thích OpenAI. `POST /api/v1/conversations/{id}/messages` trả về Server-Sent Events (SSE); đây không phải endpoint `/api/chat` của backend mẫu cũ.

## Yêu cầu

- Docker Desktop (Windows/macOS) hoặc Docker Engine và Docker Compose v2.
- Python 3.12.
- curl để kiểm tra health, theo dõi ingestion và thử chat streaming (SSE).
- [uv](https://docs.astral.sh/uv/) để đồng bộ môi trường Python theo `uv.lock`.
- Dịch vụ tương thích OpenAI cho chat và embedding có thể truy cập từ máy chạy API/worker. Với demo hoàn chỉnh, cần cấu hình cả hai dịch vụ và thông tin model tương ứng.
- Git Bash để chạy toàn bộ lệnh trong hướng dẫn; các khối script Python được truyền qua Bash heredoc và chạy bằng `uv run python -`.

## 1. Lấy mã nguồn và chuẩn bị cấu hình

Từ thư mục gốc repo:

```bash
git clone https://github.com/MinhKhoa-i/chatbot-vay-mua-nha.git
cd chatbot-vay-mua-nha/ai_service
cp .env.example .env
uv sync --locked --python 3.12
uv run python --version
```

Mở `.env` vừa tạo trong `ai_service/`, điền mật khẩu PostgreSQL riêng và cập nhật cả `DATABASE_URL` tương ứng, cùng các trường `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `EMBEDDING_BASE_URL` và `EMBEDDING_MODEL` theo nhà cung cấp đang dùng. Nếu mật khẩu chứa ký tự đặc biệt, URL-encode phần mật khẩu trong connection URL; đặt thêm `WORKER_DATABASE_URL` với host `db:5432` để worker không dùng URL tự ghép sai. Không thay `.env.example` bằng secret thật.

Các URL cần là base URL tương thích OpenAI. Adapter embedding hiện dùng chung `LLM_API_KEY` với chat (chưa hỗ trợ khóa riêng); cần gateway/provider chấp nhận cùng credential. Giữ model Qwen tương thích với adapter hiện tại: vector nguồn 4096 chiều được rút gọn/chuẩn hóa về 1536, bảng pgvector dùng 1536 chiều. Không đổi sang một embedding model bất kỳ chỉ vì cùng giao thức. Biến cấu hình chiều đúng là `EMBEDDING_DIMENSIONS=1536`.

Tạo một khóa mã hóa mới, duy nhất cho môi trường này, rồi ghi giá trị vào `DATA_ENCRYPTION_KEY_BASE64` trong `.env`:

```bash
uv run --python 3.12 python -c "import base64, secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

Nếu chưa đồng bộ môi trường, có thể dùng Python 3.12 cài sẵn trên máy thay cho `uv run`. Không chia sẻ hoặc commit `.env`/khóa. Khóa phải giữ nguyên để đọc các cuộc hội thoại đã mã hóa; thay khóa sẽ khiến dữ liệu mã hóa trước đó không giải mã được. `.env.example` là mẫu cấu hình, không phải bộ giá trị đủ để gọi provider.

Bước `uv sync --locked --python 3.12` ở trên cài dependencies theo lockfile và chọn Python 3.12 rõ ràng (không chỉ phiên bản mới nhất sẵn có). Chạy mọi lệnh `uv` và Alembic tiếp theo từ `ai_service/`; `--project ai_service` từ gốc repo không tự đổi working directory để import `app`.

## 2. Khởi động PostgreSQL trước

Từ `ai_service/`, Compose đọc `.env` và chỉ khởi động dịch vụ database khi chỉ định `db`:

```bash
docker compose up -d db
docker compose ps db
```

Compose kiểm tra trạng thái PostgreSQL bằng `pg_isready`. Đợi container `db` báo healthy trước khi chạy migration. Cổng DB chỉ bind trên loopback (`127.0.0.1`).

## 3. Tạo/cập nhật schema

Khi DB đã healthy, vẫn ở `ai_service/` và chạy migration từ máy host, nơi `DATABASE_URL` trong `.env` dùng `localhost`:

```bash
uv run alembic upgrade head
```

Các migration hiện có chuỗi `0004_knowledge` → `0005_jobs_ops` → `0006_conversations` → `0007_knowledge_activation`; `upgrade head` áp dụng toàn bộ revision còn thiếu, bao gồm cờ bật/tắt tài liệu tri thức. Alembic đọc `DATABASE_URL` từ `.env`. Nếu gặp lỗi kết nối, kiểm tra DB healthy, port, database/user/password khớp giữa `.env` và container, rồi chạy lại migration.

## 4. Chạy API và worker — mỗi thành phần đúng một lần

Mở terminal thứ nhất, từ `ai_service/`, chạy API trên host:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Kiểm tra endpoint health ở terminal khác:

```bash
curl -i http://127.0.0.1:8001/health
```

Kết quả mong đợi là HTTP 200 với `{"status":"ok"}`.

AI service chạy ở cổng **8001** vì cổng 8000 dành cho `backend/` (frontend gọi backend). Muốn bot tính được khoản trả góp thì chạy thêm backend ở cổng 8000 (xem `backend/README.md`); địa chỉ backend đặt bằng `LOAN_BACKEND_BASE_URL` trong `.env`. Hợp đồng chung giữa các phần: `docs/api.md`.

Sau khi migration xong, khởi động đúng **một** worker qua Compose ở terminal khác:

```bash
docker compose up -d --build worker
docker compose logs -f worker
```

`worker` là service đã được khai báo trong Compose và chạy `python -m app.infrastructure.jobs.worker`; không chạy thêm worker bằng `uv run python -m ...` hoặc tiến trình worker thứ hai. Worker dùng URL nội bộ `db:5432`, trong khi API/migration chạy từ host dùng `localhost`. Theo cấu hình mặc định worker gọi embedding qua `http://host.docker.internal:20128/v1`; nếu embedding gateway ở địa chỉ khác, đặt `WORKER_EMBEDDING_BASE_URL` phù hợp trong `.env` trước khi tạo/recreate worker. API đọc `EMBEDDING_BASE_URL` trực tiếp từ `.env`.

## 5. Nạp tài liệu vào kho tri thức

API nhận PDF, UTF-8 `.txt` hoặc Markdown UTF-8 `.md`; extractor **không đọc JSON trực tiếp**. Khi upload, API lưu tài liệu và xếp ingestion vào hàng đợi. Worker trích xuất nội dung, chia thành chunks, tạo embeddings rồi xuất bản. Chat chỉ truy xuất tài liệu đã được duyệt, `published` và còn hiệu lực.

Trước khi nạp, khởi động database, API và đúng một worker theo các bước 2–4. Worker cần truy cập được embedding provider. Chỉ upload sau khi thực sự kiểm tra nội dung và nguồn: API bắt buộc metadata `verified: true`, `reviewed_by` và `reviewed_at` có múi giờ. `reviewed_at` là thời điểm review, không phải thời điểm upload (database tự ghi thời điểm upload). Trong ví dụ, thay placeholder bằng thông tin review thật và giữ nguyên cùng `REVIEWED_AT` khi chạy lại cùng lần review; đổi metadata trong khi nội dung không đổi có thể gây `DOCUMENT_METADATA_CONFLICT`.

### Nạp `data/faq.json` — mỗi FAQ là một tài liệu

Script đọc JSON, tạo Markdown trong bộ nhớ và upload riêng từng FAQ qua `POST /api/v1/knowledge/documents`. Trường `source_name` được dùng làm `title` trong metadata và heading Markdown, nên phần nguồn tham khảo tự động hiển thị tên nguồn thay vì mã FAQ/câu hỏi. Tên nguồn được bỏ khoảng trắng ở hai đầu, phải có từ 1 đến 500 ký tự; script dừng nếu không hợp lệ thay vì cắt mất tên nguồn. FAQ ID, category, câu hỏi, câu trả lời, phạm vi, URL nguồn chính, nguồn bổ sung, ngày cập nhật và disclaimer vẫn được giữ trong nội dung; `source_url` và `last_updated` vẫn được gửi trong metadata. API hiện không có metadata riêng cho FAQ ID/category. Thêm `--limit 1` nếu muốn thử FAQ đầu tiên.

Script nằm sẵn ở `scripts/ingest_faq.py`. Chạy từ thư mục `ai_service/`:

```bash
# Kiểm tra file FAQ và xem 50 tài liệu sẽ gửi, chưa gửi gì
uv run python scripts/ingest_faq.py --dry-run

# Nạp thật và đợi worker xử lý xong
uv run python scripts/ingest_faq.py --reviewed-by "<tên người review>" --wait
```

- `--reviewed-by` là người đã đối chiếu nội dung FAQ với nguồn. `--reviewed-at` mặc định là thời điểm chạy; chạy lại cho **cùng lần review** thì truyền lại đúng giá trị cũ (in trong file danh sách) để tránh `DOCUMENT_METADATA_CONFLICT`.
- `--wait` đợi tới khi mọi tài liệu `published` hoặc `failed` (tối đa `--wait-timeout` giây, mặc định 600) và trả mã lỗi 1 nếu có tài liệu `failed`.
- Mỗi lần chạy thật ghi danh sách `document_id` vào `data/snapshots/faq_ingest_<thời gian>.json` (thư mục này không commit).

**Nạp lại sau khi FAQ thay đổi.** FAQ nào đổi nội dung sẽ có phiên bản mới. Retrieval chỉ dùng **phiên bản mới nhất còn hợp lệ** (đã duyệt, `published`, đang bật, còn hiệu lực) của mỗi `logical_document_id`, nên không cần làm gì thêm để bản cũ ngừng được trích dẫn. Nếu muốn dọn dẹp, có thể tắt các phiên bản đã có bản mới hơn (script cũng in câu lệnh này ở cuối); bước này không bắt buộc, nhưng giúp tránh trường hợp tắt bản mới nhất rồi bản cũ được dùng lại:

```sql
UPDATE knowledge_documents d SET is_active = false
WHERE d.is_active AND EXISTS (
    SELECT 1 FROM knowledge_documents n
    WHERE n.logical_document_id = d.logical_document_id
      AND n.version_no > d.version_no AND n.ingestion_status = 'published'
);
```

Chạy bằng `docker compose exec db psql -U <user> -d <db>` với user/database trong `.env`.

`logical_document_id = uuid5(NAMESPACE_URL, faq_id)` là UUID ổn định với đầu vào tên chỉ là ID trong JSON (ví dụ `FAQ-01`). UUID v5 vẫn cần namespace cố định `NAMESPACE_URL`; giữ nguyên namespace và FAQ ID để các lần nạp sau nhận diện cùng tài liệu logic. Không dùng lại một FAQ ID cho nội dung độc lập ở bộ dữ liệu khác khi dùng cùng namespace. `document_id` là UUID riêng do API tạo cho từng phiên bản, không phải chuỗi `FAQ-01`. Các FAQ khác ID có thể có cùng `title`; title không phải khóa định danh và các mục nguồn vẫn được nhóm theo `document_id`.

Với cùng công thức UUID, nạp lại cùng nội dung và metadata sẽ nhận diện tài liệu hiện có; nội dung thay đổi tạo phiên bản mới. Nếu cùng nội dung nhưng metadata khác, API có thể trả `DOCUMENT_METADATA_CONFLICT`.

### Nạp `docs/quy-trinh-vay.md` — một tài liệu Markdown

Tài liệu quy trình liên tục nên giữ thành một tài liệu; worker tự chia theo heading và giới hạn token. Vì đây là tài liệu tổng hợp nhiều nguồn, không gán URL của riêng một ngân hàng làm `source_url` chung; các liên kết nguồn vẫn được giữ trong nội dung.

Tạo file `scripts/ingest_loan_process.py` với nội dung sau. Sau khi lưu file, chạy lệnh ở cuối khối từ thư mục `ai_service/`.

```python
import json
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx

BASE_URL = "http://127.0.0.1:8001"
SOURCE = Path("../docs/quy-trinh-vay.md")
REVIEWED_AT = datetime.now().astimezone().isoformat()

while True:
    REVIEWED_BY = input("Nhập tên người review tài liệu: ").strip()
    if REVIEWED_BY:
        break
    print("Tên không được để trống; hãy nhập tên người review.")
reviewed_at = datetime.fromisoformat(REVIEWED_AT)
if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
    raise SystemExit("REVIEWED_AT phải có múi giờ, ví dụ +07:00 hoặc Z.")
if not SOURCE.is_file():
    raise SystemExit(f"Không tìm thấy tài liệu: {SOURCE.resolve()}")

content = SOURCE.read_bytes()
text = content.decode("utf-8-sig")
title = next(
    (line[2:].strip() for line in text.splitlines() if line.startswith("# ") and line[2:].strip()),
    SOURCE.stem,
)
logical_id = uuid5(
    NAMESPACE_URL,
    "/docs/quy-trinh-vay.md",
)
metadata = {
    "title": title,
    "verified": True,
    "reviewed_by": REVIEWED_BY,
    "reviewed_at": REVIEWED_AT,
    "logical_document_id": str(logical_id),
}

with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
    response = client.post(
        "/api/v1/knowledge/documents",
        data={"metadata": json.dumps(metadata, ensure_ascii=False)},
        files={"file": (SOURCE.name, content, "text/markdown")},
    )
    if response.is_error:
        raise SystemExit(f"HTTP {response.status_code}\n{response.text}")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))
```

Chạy từ thư mục `ai_service/`:

```bash
uv run python scripts/ingest_loan_process.py
```

### Theo dõi ingestion và kiểm tra câu trả lời

Upload thường trả `ingestion_status: queued` cùng `document_id`. Kiểm tra bằng ID trong response đến khi trạng thái là `published`:

```bash
document_id="UUID_NHAN_DUOC_TU_RESPONSE"
curl -sS "http://127.0.0.1:8001/api/v1/knowledge/documents/${document_id}"
```

Nếu trạng thái `failed` hoặc `queued` kéo dài, xem log worker/provider bằng `docker compose logs --tail 100 worker`. Khi đã `published`, thử câu hỏi tương ứng với FAQ và từng bước trong quy trình vay; kiểm tra câu trả lời bám bằng chứng, trích đúng nguồn và không gộp điều kiện giữa các ngân hàng. Disclaimer được giữ trong nội dung FAQ; với câu trả lời retrieval có gọi model, prompt yêu cầu model tự viết một câu disclaimer ngắn trước footer nguồn. Đây là hướng dẫn prompt, không phải bảo đảm được kiểm tra ở runtime; greeting, câu trả lời xác định và phản hồi khi thiếu bằng chứng không có disclaimer model. `published` xác nhận ingestion hoàn tất, không tự chứng minh chất lượng retrieval.

## 6. Thử chat streaming bằng curl

Tạo conversation trước bằng endpoint riêng:

```bash
curl -sS -X POST http://127.0.0.1:8001/api/v1/conversations \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Lấy `conversation_id` từ response rồi gán vào biến bên dưới. Mỗi lượt cần UUID mới cho `client_request_id`; conversation vừa tạo bắt đầu với `expected_version: 0`, còn lượt tiếp theo phải dùng version mới nhất do API trả về. Có thể bỏ bước tạo riêng nếu tự tạo một UUIDv4 cho path; lượt chat hợp lệ đầu tiên sẽ tạo conversation đó. Ví dụ nhanh cho lượt đầu:

```bash
CONVERSATION_ID='<conversation_id từ response tạo conversation>'
CLIENT_REQUEST_ID="$(uv run python -c 'import uuid; print(uuid.uuid4())')"
curl -N -sS -X POST "http://127.0.0.1:8001/api/v1/conversations/${CONVERSATION_ID}/messages" \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d "{\"client_request_id\":\"${CLIENT_REQUEST_ID}\",\"text\":\"Tôi cần chuẩn bị hồ sơ gì để vay mua nhà?\",\"expected_version\":0}"
```

`-N` tắt buffering của curl để hiển thị các event khi nhận được. SSE có dạng `event: delta` cùng `data: {"text":"..."}` cho từng đoạn; khi hoàn tất có `event: done` với kết quả đã lưu. Với câu hỏi tiếng Việt về hồ sơ vay, nếu FAQ đã được ingest thành công và embedding hoạt động, câu trả lời dự kiến sẽ dựa trên tài liệu đã duyệt và có thể kèm dòng `Nguồn tham khảo`.

Ví dụ **nội dung mong đợi**, không phải kết quả đã đo từ provider:

> Hồ sơ vay mua nhà thường gồm giấy đề nghị vay vốn/phương án trả nợ, giấy tờ nhân thân, giấy tờ chứng minh mục đích vay, hồ sơ chứng minh thu nhập và hồ sơ tài sản bảo đảm. Danh mục cụ thể phụ thuộc ngân hàng/sản phẩm; bạn cần xác nhận trực tiếp với ngân hàng. [1]

Nội dung thực tế và mã trích dẫn phụ thuộc các chunks được truy xuất; không cam kết câu trả lời cố định. Để thử phản hồi xác định không cần model/embedding, thay `text` bằng `Xin chào` trong một conversation mới: nhận lời chào tiếng Việt và thông tin rằng AI service có thể ước tính khoản trả góp niên kim với lãi suất cố định toàn kỳ sau khi thu thập và xác nhận đủ dữ liệu; luồng này không đánh giá khả năng vay hay khả năng chi trả, rồi event `done`. Lượt chào vẫn cần PostgreSQL và khóa mã hóa hợp lệ để lưu hội thoại.

## Endpoint chính và lỗi thường gặp

- `GET /health` — health check, không kiểm tra khả năng truy cập LLM/embedding.
- `POST /api/v1/conversations` — tạo conversation.
- `GET /api/v1/conversations/{conversation_id}` — đọc trạng thái/version hiện tại.
- `GET /api/v1/conversations/{conversation_id}/messages` — xem lịch sử hội thoại.
- `DELETE /api/v1/conversations/{conversation_id}` — xóa conversation.
- `POST /api/v1/conversations/{conversation_id}/messages` — gửi lượt chat SSE.
- `POST /api/v1/knowledge/documents` — tải tài liệu multipart; metadata form field là JSON string.
- `GET /api/v1/knowledge/documents/{document_id}` — kiểm tra trạng thái ingestion và cờ `is_active`.
- `PATCH /api/v1/knowledge/documents/{document_id}/activation` — bật/tắt tài liệu khỏi retrieval, body ví dụ `{"is_active": false}`. Chỉ tài liệu được `approved`, `published`, đang active và còn hiệu lực mới được truy xuất. Muốn ẩn hẳn một tài liệu khỏi retrieval, cần tắt tất cả phiên bản có cùng `logical_document_id`; chỉ tắt phiên bản mới nhất thì phiên bản cũ hơn còn bật và đủ điều kiện có thể được dùng lại.

Chat request yêu cầu `client_request_id` UUID và `text` từ 1–4000 ký tự; không cho phép field lạ. Thân request tối đa 20 KiB. Lỗi validate thường trả HTTP 422; ID/version cũ có thể tạo event `error` như `CONVERSATION_NOT_FOUND` hoặc `VERSION_CONFLICT`. Provider/migration/config chưa sẵn sàng có thể dẫn đến HTTP 503 hoặc event SSE `error`; các mã thường gặp gồm `MODEL_NOT_CONFIGURED`, `MODEL_UNAVAILABLE`, `MODEL_RATE_LIMITED`, `RETRIEVAL_NOT_CONFIGURED`, `EMBEDDING_UNAVAILABLE`, `KNOWLEDGE_SEARCH_UNAVAILABLE`, `STATE_UNAVAILABLE` và `INTERNAL_ERROR`. Event lỗi bên trong stream có thể vẫn đi cùng HTTP 200 vì response SSE đã bắt đầu; đọc event `error`, không chỉ dựa vào status HTTP. Không gửi lại cùng request ID với nội dung khác.

## Giới hạn và lưu ý bảo mật

- Đây là demo, chưa phải hệ thống tư vấn tín dụng/duyệt vay. Có mô phỏng trả góp qua backend (niên kim hoặc gốc đều, lãi cố định hoặc một giai đoạn ưu đãi rồi một mức lãi); không có đánh giá khả năng chi trả hoặc endpoint phê duyệt vay trong AI service. Không coi nội dung chatbot là báo giá, lãi suất hiện hành hoặc cam kết duyệt vay.
- Demo không có xác thực/ủy quyền cho API hội thoại, upload hoặc endpoint `PATCH /api/v1/knowledge/documents/{document_id}/activation` để bật/tắt tài liệu tri thức. Không mở cổng ra Internet, không đưa dữ liệu khách hàng thật lên môi trường chia sẻ và chỉ cho người vận hành đáng tin dùng endpoint upload hoặc bật/tắt tài liệu. CORS cho phép origin frontend local, nhưng CORS không phải cơ chế xác thực.
- Nội dung hội thoại được mã hóa AES-256-GCM bằng `DATA_ENCRYPTION_KEY_BASE64`; hãy bảo vệ và sao lưu khóa an toàn. Mất khóa đồng nghĩa không đọc được payload đã mã hóa. Không đặt khóa thật trong git, log, issue hoặc lệnh shell được chia sẻ.
- FAQ demo phải được đối chiếu với nguồn gốc và tình trạng hiệu lực trước khi đánh dấu verified. Tài liệu không được review không nên upload dưới dạng tài liệu đã duyệt; câu trả lời retrieval chỉ nên căn cứ vào nguồn đã được nạp/duyệt. API/provider vẫn có thể lỗi hoặc dữ liệu có thể cũ.
- Snapshot lưu trong `ai_service/data/snapshots/`; PostgreSQL lưu metadata, chunks/vector và trạng thái. Docker volume database giữ dữ liệu qua lần dừng container. Demo không cấu hình backup, quản lý secret, xoay khóa hay quy trình xóa an toàn cho production.

## Kiểm thử và tài liệu liên quan

Từ gốc repo, chạy test mà không gọi model/embedding thật:

```bash
uv run --directory ai_service --extra test python -m pytest -q
```

Bộ test không thay thế kiểm thử DB/worker/provider thật. `GET /health` cũng không xác nhận migration hoặc provider đã sẵn sàng. Xem [thiết kế chatbot và kế hoạch tích hợp calculator](../docs/chatbot-design.md), [hợp đồng chat SSE](docs/chat-streaming-api.md) và [hợp đồng hội thoại](docs/conversation-api.md).

## Xử lý secret đã lộ

Notebook nháp, `.agents/` và snapshot runtime đã được bỏ theo dõi và ignore; bản local vẫn có thể tồn tại. `git rm --cached` không xóa secret trong lịch sử Git, fork, cache hoặc bản clone cũ.

- API key từng ghi trong notebook: chủ sở hữu phải thu hồi/đổi tại provider, rà soát usage và cập nhật secret local/triển khai. Không dùng API key đó để kiểm tra còn sống hay không.
- Khóa mã hóa mẫu cũ: nếu từng dùng thật, cần thay khóa theo quy trình có backup và tái mã hóa dữ liệu; chỉ thay biến môi trường sẽ làm payload cũ không đọc được. Demo không có dữ liệu cần giữ có thể dùng DB demo mới với khóa mới; không xóa volume dữ liệu thật để xử lý sự cố.
- Sau khi khóa đã bị vô hiệu hóa, phối hợp với nhóm nếu cần làm sạch lịch sử; không tự force-push/rewrite lịch sử của cả nhóm.

## Dừng môi trường demo

```bash
docker compose stop worker db
```

Lệnh này dừng worker và database, giữ lại volume database. Dừng API bằng `Ctrl+C` tại terminal đang chạy Uvicorn. Không dùng `docker compose down -v` trừ khi chủ đích xóa vĩnh viễn dữ liệu DB demo.
