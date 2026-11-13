"""Nạp data/faq.json vào kho tri thức của ai_service, mỗi FAQ là một tài liệu Markdown.

Chạy từ thư mục ai_service/ (cần API và đúng một worker đang chạy, xem README mục 5):
    uv run python scripts/ingest_faq.py --dry-run
    uv run python scripts/ingest_faq.py --reviewed-by "Minh Khoa" --wait

Cùng FAQ ID luôn có cùng logical_document_id; nội dung đổi thì API tạo phiên bản mới.
Phiên bản cũ KHÔNG tự tắt: xem SQL in ra ở cuối để tắt các phiên bản đã có bản mới hơn.
"""

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx

AI_SERVICE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = AI_SERVICE_DIR.parent / "data" / "faq.json"
MANIFEST_DIR = AI_SERVICE_DIR / "data" / "snapshots"
REQUIRED_FIELDS = ("id", "category", "question", "answer", "source_name")
DEACTIVATE_OLD_SQL = """UPDATE knowledge_documents d SET is_active = false
WHERE d.is_active AND EXISTS (
    SELECT 1 FROM knowledge_documents n
    WHERE n.logical_document_id = d.logical_document_id
      AND n.version_no > d.version_no AND n.ingestion_status = 'published'
);"""


def logical_id(faq_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, faq_id)


def load_faqs(source: Path) -> tuple[dict, list[dict]]:
    data = json.loads(source.read_text(encoding="utf-8"))
    items = data.get("faqs")
    if not isinstance(items, list) or not items:
        raise SystemExit(f"{source}: không có danh sách 'faqs'.")
    ids = [item.get("id") for item in items]
    duplicates = sorted(i for i, n in Counter(ids).items() if n > 1)
    if duplicates:
        raise SystemExit(f"FAQ ID bị trùng: {', '.join(map(str, duplicates))}")
    for item in items:
        missing = [name for name in REQUIRED_FIELDS if not str(item.get(name) or "").strip()]
        if missing:
            raise SystemExit(f"{item.get('id', '?')}: thiếu trường {', '.join(missing)}.")
        if not 1 <= len(item["source_name"].strip()) <= 500:
            raise SystemExit(f"{item['id']}: source_name phải có từ 1 đến 500 ký tự.")
    return data, items


def build_markdown(item: dict, disclaimer: str) -> bytes:
    lines = [
        f"# {item['source_name'].strip()}", "", f"FAQ ID: {item['id']}",
        f"Chủ đề: {item['category']}", "",
        f"Câu hỏi: {item['question']}", "",
        f"Trả lời: {item['answer']}", "",
        f"Phạm vi áp dụng: {item.get('applicable_scope', '')}",
        f"Nguồn: {item.get('source_name', '')}",
        f"URL: {item.get('source_url', '')}",
        "Nguồn bổ sung: " + ", ".join(item.get("additional_sources", [])),
        f"Cập nhật nội dung: {item.get('last_updated', '')}", "",
        disclaimer,
    ]
    return "\n".join(lines).encode("utf-8")


def build_metadata(item: dict, reviewed_by: str, reviewed_at: str) -> dict:
    metadata = {
        "title": item["source_name"].strip(),
        "verified": True,
        "reviewed_by": reviewed_by,
        "reviewed_at": reviewed_at,
        "logical_document_id": str(logical_id(item["id"])),
    }
    if item.get("source_url"):
        metadata["source_url"] = item["source_url"]
    if item.get("last_updated"):
        metadata["last_updated"] = item["last_updated"]
    return metadata


def upload(client: httpx.Client, item: dict, disclaimer: str, reviewed_by: str, reviewed_at: str) -> dict:
    response = client.post(
        "/api/v1/knowledge/documents",
        data={"metadata": json.dumps(build_metadata(item, reviewed_by, reviewed_at), ensure_ascii=False)},
        files={"file": (f"{item['id']}.md", build_markdown(item, disclaimer), "text/markdown")},
    )
    if response.is_error:
        raise SystemExit(f"{item['id']}: HTTP {response.status_code}\n{response.text}")
    return response.json()


def wait_until_done(client: httpx.Client, document_ids: dict[str, str], timeout: float,
                    interval: float = 3.0, sleep=time.sleep) -> dict[str, str]:
    """Đợi các tài liệu chuyển sang published/failed; trả về {faq_id: trạng thái cuối}."""
    status = {faq_id: "queued" for faq_id in document_ids}
    deadline = time.monotonic() + timeout
    while True:
        for faq_id, document_id in document_ids.items():
            if status[faq_id] in {"published", "failed"}:
                continue
            response = client.get(f"/api/v1/knowledge/documents/{document_id}")
            if response.is_success:
                status[faq_id] = response.json().get("ingestion_status", status[faq_id])
        if all(s in {"published", "failed"} for s in status.values()) or time.monotonic() >= deadline:
            return status
        sleep(interval)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nạp data/faq.json vào kho tri thức ai_service")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--reviewed-by", help="Tên người đã đối chiếu nội dung FAQ với nguồn")
    parser.add_argument("--reviewed-at", help="Thời điểm review, ISO 8601 có múi giờ (mặc định: bây giờ). "
                                              "Chạy lại cùng lần review thì truyền lại đúng giá trị cũ.")
    parser.add_argument("--limit", type=int, help="Chỉ nạp N FAQ đầu tiên (để thử)")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ kiểm tra và in tóm tắt, không gửi")
    parser.add_argument("--wait", action="store_true", help="Đợi tới khi mọi tài liệu published/failed")
    parser.add_argument("--wait-timeout", type=float, default=600.0, help="Số giây tối đa khi --wait")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(sys.argv[1:] if argv is None else argv)
    data, items = load_faqs(args.source)
    if args.limit is not None:
        items = items[:args.limit]
    disclaimer = data.get("disclaimer", "")
    categories = Counter(item["category"] for item in items)
    summary = ", ".join(f"{k}: {v}" for k, v in sorted(categories.items()))
    print(f"{len(items)} FAQ từ {args.source} | {summary}")

    if args.dry_run:
        for item in items:
            print(f"  {item['id']}  {logical_id(item['id'])}  {len(build_markdown(item, disclaimer))} byte  "
                  f"{item['source_name'].strip()[:60]}")
        print("Chạy thử: chưa gửi gì lên ai_service.")
        return 0

    reviewed_by = (args.reviewed_by or "").strip()
    if not reviewed_by:
        raise SystemExit("Cần --reviewed-by: tên người đã đối chiếu nội dung FAQ với nguồn.")
    reviewed_at = args.reviewed_at or datetime.now().astimezone().isoformat(timespec="seconds")
    parsed = datetime.fromisoformat(reviewed_at)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SystemExit("--reviewed-at phải có múi giờ, ví dụ 2026-11-13T20:00:00+07:00.")

    results: dict[str, dict] = {}
    with httpx.Client(base_url=args.base_url, timeout=60.0) as client:
        for item in items:
            results[item["id"]] = upload(client, item, disclaimer, reviewed_by, reviewed_at)
            print(f"{item['id']}: document_id={results[item['id']]['document_id']} "
                  f"status={results[item['id']]['ingestion_status']}")
        final = {faq_id: r["ingestion_status"] for faq_id, r in results.items()}
        if args.wait:
            print("Đang đợi worker xử lý...")
            final = wait_until_done(client, {k: r["document_id"] for k, r in results.items()},
                                    args.wait_timeout)

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest = MANIFEST_DIR / f"faq_ingest_{datetime.now():%Y%m%d_%H%M%S}.json"
    manifest.write_text(json.dumps({
        "reviewed_by": reviewed_by, "reviewed_at": reviewed_at, "source": str(args.source),
        "documents": {k: {**r, "final_status": final[k]} for k, r in results.items()},
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = Counter(final.values())
    summary = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    print(f"Kết quả: {summary} | Danh sách: {manifest}")
    print("Tài liệu FAQ đã sửa nội dung có thêm phiên bản mới, nhưng phiên bản cũ vẫn được truy xuất.\n"
          "Sau khi các bản mới published, tắt bản cũ bằng SQL (ví dụ: docker compose exec db psql "
          "-U <user> -d <db>):\n" + DEACTIVATE_OLD_SQL)
    return 0 if set(final.values()) <= {"published"} or not args.wait else 1


if __name__ == "__main__":
    raise SystemExit(main())
