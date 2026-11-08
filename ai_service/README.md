# AI Service — hướng dẫn chạy demo cục bộ

Hướng dẫn này dành cho môi trường demo phát triển, không phải cấu hình triển khai production. AI service là ứng dụng riêng trong `ai_service/`, dùng PostgreSQL + pgvector, một worker xử lý ingestion, dịch vụ embedding tương thích OpenAI và dịch vụ chat tương thích OpenAI. `POST /api/v1/conversations/{id}/messages` trả về Server-Sent Events (SSE); đây không phải endpoint `/api/chat` của backend mẫu cũ.

## Yêu cầu

- Docker Desktop (Windows/macOS) hoặc Docker Engine và Docker Compose v2.
- Python 3.12.
- [uv](https://docs.astral.sh/uv/) để đồng bộ môi trường Python theo `uv.lock`.
- Dịch vụ tương thích OpenAI cho chat và embedding có thể truy cập từ máy chạy API/worker. Với demo hoàn chỉnh, cần cấu hình cả hai dịch vụ và thông tin model tương ứng.
- `curl` để gọi API. Các lệnh dưới đây dùng cú pháp Bash (Linux/macOS, WSL hoặc Git Bash).

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

Migration hiện có chuỗi `0004_knowledge` → `0005_jobs_ops` → `0006_conversations`; `upgrade head` áp dụng toàn bộ revision còn thiếu. Alembic đọc `DATABASE_URL` từ `.env`. Nếu gặp lỗi kết nối, kiểm tra DB healthy, port, database/user/password khớp giữa `.env` và container, rồi chạy lại migration.

## 4. Chạy API và worker — mỗi thành phần đúng một lần

Mở terminal thứ nhất, từ `ai_service/`, chạy API trên host:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Kiểm tra endpoint health ở terminal khác:

```bash
curl -i http://127.0.0.1:8000/health
```

Kết quả mong đợi là HTTP 200 với `{"status":"ok"}`.

Sau khi migration xong, khởi động đúng **một** worker qua Compose ở terminal khác:

```bash
docker compose up -d --build worker
docker compose logs -f worker
```

`worker` là service đã được khai báo trong Compose và chạy `python -m app.infrastructure.jobs.worker`; không chạy thêm worker bằng `uv run python -m ...` hoặc tiến trình worker thứ hai. Worker dùng URL nội bộ `db:5432`, trong khi API/migration chạy từ host dùng `localhost`. Theo cấu hình mặc định worker gọi embedding qua `http://host.docker.internal:20128/v1`; nếu embedding gateway ở địa chỉ khác, đặt `WORKER_EMBEDDING_BASE_URL` phù hợp trong `.env` trước khi tạo/recreate worker. API đọc `EMBEDDING_BASE_URL` trực tiếp từ `.env`.

## 5. Đưa FAQ demo vào knowledge base

API hiện nhận file PDF, văn bản UTF-8 `.txt` hoặc Markdown UTF-8 `.md`; extractor **không đọc JSON**. Không gửi trực tiếp `data/faq.json` dưới đuôi `.json`. Cách dưới đây chuyển FAQ JSON thành Markdown UTF-8 tạm trong thư mục snapshot (không sửa file JSON nguồn). Chỉ upload nội dung sau khi người vận hành đã kiểm tra/duyệt tính chính xác của nguồn: API yêu cầu metadata xác nhận `verified: true`, `reviewed_by` và `reviewed_at` có múi giờ. Ví dụ metadata dưới đây là dữ liệu demo; hãy thay reviewer/ngày và URL nguồn bằng thông tin đã kiểm tra, không khai khống việc review.

Tại terminal `ai_service/`, từ Bash chạy đoạn chuyển đổi:

```bash
uv run python - <<'PY'
import json
from pathlib import Path

source = Path("../data/faq.json")
out = Path("data/snapshots/faq-demo.md")
data = json.loads(source.read_text(encoding="utf-8"))
lines = [f"# {data['title']}", "", data.get("disclaimer", ""), ""]
for item in data["faqs"]:
    lines.extend([
        f"## {item['id']} — {item['category']}",
        "",
        f"**Câu hỏi:** {item['question']}",
        "",
        f"**Trả lời:** {item['answer']}",
        "",
        f"**Phạm vi:** {item.get('applicable_scope', '')}",
        f"**Nguồn:** {item.get('source_name', '')}",
        f"**URL:** {item.get('source_url', '')}",
        f"**Cập nhật nội dung:** {item.get('last_updated', '')}",
        "",
    ])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines), encoding="utf-8")
print(f"Đã tạo {out} — kiểm tra nội dung trước khi upload.")
PY
```

Kiểm tra Markdown được tạo và các URL nguồn trước khi upload. Tạo conversation (ghi lại `conversation_id` trong JSON trả về):

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/conversations \
  -H 'Content-Type: application/json'
```

Upload tài liệu bằng multipart form. Thay `reviewer-demo` và ngày giờ bằng lần review thực tế, có timezone; dùng nguồn đã kiểm tra (hoặc bỏ `source_url` nếu chưa có URL đáng tin cậy). `verified` bắt buộc là `true`:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/knowledge/documents \
  -F 'file=@data/snapshots/faq-demo.md;type=text/markdown' \
  -F 'metadata={"title":"FAQ quy trình vay mua nhà (demo)","verified":true,"reviewed_by":"reviewer-demo","reviewed_at":"2026-11-08T10:00:00Z"}'
```

Nếu thành công, response trả `document_id` và `ingestion_status` thường ban đầu là `queued`. Ghi lại `document_id`, xem tiến trình bằng endpoint dưới đây và đợi đến khi `ingestion_status` là `published`:

```bash
DOCUMENT_ID='<document_id từ response upload>'
curl -sS "http://127.0.0.1:8000/api/v1/knowledge/documents/${DOCUMENT_ID}"
```

Worker cần truy cập được embedding provider để biến tài liệu thành chunks/vector. Nếu upload bị `UNSUPPORTED_FILE_TYPE`, hãy dùng `.md`, `.txt` hoặc PDF; nếu trạng thái `failed`, xem log worker/provider và mã lỗi trả về. Có thể theo dõi log bằng `docker compose logs -f worker`.

## 6. Thử chat streaming bằng curl

Tạo conversation như bước trên, rồi gán UUID thực tế đã nhận. Mỗi lượt cần UUID mới cho `client_request_id`; conversation vừa tạo bắt đầu với `expected_version: 0`, còn lượt tiếp theo phải dùng version mới nhất do API trả về. Ví dụ nhanh cho lượt đầu:

```bash
CONVERSATION_ID='<conversation_id từ bước tạo>'
CLIENT_REQUEST_ID="$(uv run python -c 'import uuid; print(uuid.uuid4())')"
curl -N -sS -X POST "http://127.0.0.1:8000/api/v1/conversations/${CONVERSATION_ID}/messages" \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d "{\"client_request_id\":\"${CLIENT_REQUEST_ID}\",\"text\":\"Tôi cần chuẩn bị hồ sơ gì để vay mua nhà?\",\"expected_version\":0}"
```

`-N` tắt buffering của curl để hiển thị các event khi nhận được. SSE có dạng `event: delta` cùng `data: {"text":"..."}` cho từng đoạn; khi hoàn tất có `event: done` với kết quả đã lưu. Với câu hỏi tiếng Việt về hồ sơ vay, nếu FAQ đã được ingest thành công và embedding hoạt động, câu trả lời dự kiến sẽ dựa trên tài liệu đã duyệt và có thể kèm dòng `Nguồn tham khảo`.

Ví dụ **nội dung mong đợi**, không phải kết quả đã đo từ provider:

> Hồ sơ vay mua nhà thường gồm giấy đề nghị vay vốn/phương án trả nợ, giấy tờ nhân thân, giấy tờ chứng minh mục đích vay, hồ sơ chứng minh thu nhập và hồ sơ tài sản bảo đảm. Danh mục cụ thể phụ thuộc ngân hàng/sản phẩm; bạn cần xác nhận trực tiếp với ngân hàng. [1]

Nội dung thực tế và mã trích dẫn phụ thuộc các chunks được truy xuất; không cam kết câu trả lời cố định. Để thử phản hồi xác định không cần model/embedding, thay `text` bằng `Xin chào` trong một conversation mới: nhận lời chào tiếng Việt cùng thông báo **chưa hỗ trợ tính khoản trả góp hoặc ước tính khả năng vay**, rồi event `done`. Lượt chào vẫn cần PostgreSQL và khóa mã hóa hợp lệ để lưu hội thoại.

## Endpoint chính và lỗi thường gặp

- `GET /health` — health check, không kiểm tra khả năng truy cập LLM/embedding.
- `POST /api/v1/conversations` — tạo conversation.
- `GET /api/v1/conversations/{conversation_id}` — đọc trạng thái/version hiện tại.
- `GET /api/v1/conversations/{conversation_id}/messages` — xem lịch sử hội thoại.
- `DELETE /api/v1/conversations/{conversation_id}` — xóa conversation.
- `POST /api/v1/conversations/{conversation_id}/messages` — gửi lượt chat SSE.
- `POST /api/v1/knowledge/documents` — tải tài liệu multipart; metadata form field là JSON string.
- `GET /api/v1/knowledge/documents/{document_id}` — kiểm tra trạng thái ingestion.

Chat request yêu cầu `client_request_id` UUID và `text` từ 1–4000 ký tự; không cho phép field lạ. Thân request tối đa 20 KiB. Lỗi validate thường trả HTTP 422; ID/version cũ có thể tạo event `error` như `CONVERSATION_NOT_FOUND` hoặc `VERSION_CONFLICT`. Provider/migration/config chưa sẵn sàng có thể dẫn đến HTTP 503 hoặc event SSE `error`; các mã thường gặp gồm `MODEL_NOT_CONFIGURED`, `MODEL_UNAVAILABLE`, `MODEL_RATE_LIMITED`, `RETRIEVAL_NOT_CONFIGURED`, `EMBEDDING_UNAVAILABLE`, `KNOWLEDGE_SEARCH_UNAVAILABLE`, `STATE_UNAVAILABLE` và `INTERNAL_ERROR`. Event lỗi bên trong stream có thể vẫn đi cùng HTTP 200 vì response SSE đã bắt đầu; đọc event `error`, không chỉ dựa vào status HTTP. Không gửi lại cùng request ID với nội dung khác.

## Giới hạn và lưu ý bảo mật

- Đây là demo, chưa phải hệ thống tư vấn tín dụng/duyệt vay. Không có endpoint máy tính khoản vay trong AI service này; không coi nội dung chatbot là báo giá, lãi suất hiện hành hoặc cam kết duyệt vay.
- Demo không có xác thực/ủy quyền cho API hội thoại hoặc upload. Không mở cổng ra Internet, không đưa dữ liệu khách hàng thật lên môi trường chia sẻ và chỉ cho người vận hành đáng tin dùng endpoint upload. CORS cho phép origin frontend local, nhưng CORS không phải cơ chế xác thực.
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
