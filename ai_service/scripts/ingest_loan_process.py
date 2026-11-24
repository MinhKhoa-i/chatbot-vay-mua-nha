import json
import os
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx

BASE_URL = "http://127.0.0.1:8001"
ADMIN_API_KEY = os.environ["ADMIN_API_KEY"]
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

with httpx.Client(base_url=BASE_URL, timeout=60.0, headers={"X-Admin-Key": ADMIN_API_KEY}) as client:
    response = client.post(
        "/api/v1/knowledge/documents",
        data={"metadata": json.dumps(metadata, ensure_ascii=False)},
        files={"file": (SOURCE.name, content, "text/markdown")},
    )
    if response.is_error:
        raise SystemExit(f"HTTP {response.status_code}\n{response.text}")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))