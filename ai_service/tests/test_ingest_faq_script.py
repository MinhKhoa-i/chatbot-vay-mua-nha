import json
import os
import subprocess
import sys
from collections import Counter
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import ingest_faq

def test_repository_faq_file_has_90_entries_in_7_categories():
    data, items = ingest_faq.load_faqs(ingest_faq.DEFAULT_SOURCE)
    assert len(items) == 90
    assert [item["id"] for item in items] == [f"FAQ-{i:02d}" for i in range(1, 91)]
    assert set(Counter(item["category"] for item in items)) == {
        "DIEU_KIEN_VAY",
        "HO_SO_PHAP_LY",
        "LAI_SUAT",
        "PHI_TRA_TRUOC_HAN",
        "BAO_HIEM_KHOAN_VAY",
        "RUI_RO",
        "LOI_KHUYEN",
    }
    assert Counter(item["category"] for item in items)["RUI_RO"] == 15
    assert Counter(item["category"] for item in items)["LOI_KHUYEN"] == 15
    assert data["disclaimer"]


def test_markdown_and_metadata_keep_source_and_stable_logical_id():
    data, items = ingest_faq.load_faqs(ingest_faq.DEFAULT_SOURCE)
    item = items[0]
    body = ingest_faq.build_markdown(item, data["disclaimer"]).decode("utf-8")
    assert body.startswith(f"# {item['source_name'].strip()}")
    assert f"FAQ ID: {item['id']}" in body and item["answer"] in body and data["disclaimer"] in body
    metadata = ingest_faq.build_metadata(item, "Minh Khoa", "2026-11-13T20:00:00+07:00")
    assert metadata["logical_document_id"] == str(uuid5(NAMESPACE_URL, item["id"]))
    assert metadata["verified"] is True and metadata["source_url"] == item["source_url"]


@pytest.mark.parametrize("faqs, message", [
    ([{"id": "FAQ-01", "category": "A", "question": "q", "answer": "a", "source_name": "s"}] * 2, "trùng"),
    ([{"id": "FAQ-01", "category": "A", "question": "q", "answer": "", "source_name": "s"}], "answer"),
    ([{"id": "FAQ-01", "category": "A", "question": "q", "answer": "a", "source_name": "x" * 501}], "500"),
])
def test_invalid_faq_file_is_rejected(tmp_path, faqs, message):
    source = tmp_path / "faq.json"
    _, items = ingest_faq.load_faqs(ingest_faq.DEFAULT_SOURCE)
    faqs = [{**items[0], **faq} for faq in faqs]
    source.write_text(json.dumps({"faqs": faqs}), encoding="utf-8")
    with pytest.raises(SystemExit, match=message):
        ingest_faq.load_faqs(source)


def test_upload_then_wait_until_published():
    polls = Counter()

    def handler(request):
        assert request.headers["X-Admin-Key"] == "test-admin-key"
        if request.method == "POST":
            assert request.url.path == "/api/v1/knowledge/documents"
            assert b'"logical_document_id"' in request.content
            return httpx.Response(202, json={"document_id": "d1", "ingestion_status": "queued"})
        polls[request.url.path] += 1
        status = "processing" if polls[request.url.path] < 2 else "published"
        return httpx.Response(200, json={"document_id": "d1", "ingestion_status": status})

    data, items = ingest_faq.load_faqs(ingest_faq.DEFAULT_SOURCE)
    with httpx.Client(
        base_url="http://ai.test",
        transport=httpx.MockTransport(handler),
        headers={"X-Admin-Key": "test-admin-key"},
    ) as client:
        result = ingest_faq.upload(
            client, items[0], data["disclaimer"], "Minh Khoa", "2026-11-13T20:00:00+07:00",
        )
        assert result["ingestion_status"] == "queued"
        final = ingest_faq.wait_until_done(client, {items[0]["id"]: "d1"}, timeout=5, sleep=lambda _: None)
    assert final == {items[0]["id"]: "published"}


def test_non_dry_run_requires_admin_api_key(monkeypatch):
    monkeypatch.setattr(ingest_faq, "get_settings", lambda: type("Settings", (), {"admin_api_key": ""})())

    with pytest.raises(SystemExit, match="Thiếu ADMIN_API_KEY"):
        ingest_faq.main(["--reviewed-by", "Minh Khoa"])


@pytest.mark.parametrize("status, detail", [
    (401, "UNAUTHORIZED"),
    (403, "FORBIDDEN"),
    (409, "conflict"),
    (409, "IDEMPOTENCY_KEY_REUSED"),
    (422, "INVALID_METADATA"),
    (500, "DOCUMENT_METADATA_CONFLICT"),
    (503, "KNOWLEDGE_STORAGE_UNAVAILABLE"),
])
def test_upload_error_stops_with_faq_id(status, detail):
    data, items = ingest_faq.load_faqs(ingest_faq.DEFAULT_SOURCE)
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json={"detail": detail}))
    with httpx.Client(base_url="http://ai.test", transport=transport) as client:
        with pytest.raises(SystemExit, match=items[0]["id"]):
            ingest_faq.upload(client, items[0], data["disclaimer"], "Minh Khoa", "2026-11-13T20:00:00+07:00")


@pytest.mark.parametrize("response", [
    httpx.Response(409, text="DOCUMENT_METADATA_CONFLICT"),
    httpx.Response(409, json={"detail": "not DOCUMENT_METADATA_CONFLICT"}),
    httpx.Response(409, json=["DOCUMENT_METADATA_CONFLICT"]),
    httpx.Response(409, json={"detail": {"code": "DOCUMENT_METADATA_CONFLICT"}}),
])
def test_upload_does_not_skip_unrecognized_conflict(response):
    data, items = ingest_faq.load_faqs(ingest_faq.DEFAULT_SOURCE)
    with httpx.Client(base_url="http://ai.test", transport=httpx.MockTransport(lambda _: response)) as client:
        with pytest.raises(SystemExit, match="FAQ-01: HTTP 409"):
            ingest_faq.upload(client, items[0], data["disclaimer"], "Minh Khoa", "2026-11-26T10:00:00+07:00")


@pytest.mark.parametrize("skipped_count, existing_status, worker_status", [
    (1, 409, "published"),
    (3, 409, "published"),
    (1, 200, "published"),
    (1, 409, "failed"),
    (1, 409, "processing"),
])
def test_main_skips_existing_and_waits_only_for_new_documents(
    tmp_path, monkeypatch, capsys, skipped_count, existing_status, worker_status,
):
    posts, polls = [], []
    client_type = httpx.Client

    def handler(request):
        if request.method == "POST":
            faq_id = f"FAQ-{len(posts) + 1:02d}"
            posts.append(faq_id)
            if len(posts) <= skipped_count:
                if existing_status == 409:
                    return httpx.Response(409, json={"detail": "DOCUMENT_METADATA_CONFLICT"})
                return httpx.Response(200, json={
                    "document_id": f"existing-{faq_id}", "ingestion_status": "published",
                })
            return httpx.Response(202, json={"document_id": faq_id, "ingestion_status": "queued"})
        polls.append(request.url.path)
        return httpx.Response(200, json={"ingestion_status": worker_status})

    monkeypatch.setattr(ingest_faq, "get_settings", lambda: type("Settings", (), {"admin_api_key": "test-key"})())
    monkeypatch.setattr(ingest_faq, "MANIFEST_DIR", tmp_path)
    monkeypatch.setattr(ingest_faq.httpx, "Client", lambda **kwargs: client_type(
        **kwargs, transport=httpx.MockTransport(handler),
    ))
    exit_code = ingest_faq.main([
        "--limit", "3", "--reviewed-by", "Người kiểm thử", "--wait",
        "--reviewed-at", "2026-11-26T10:00:00+07:00", "--wait-timeout", "0",
    ])
    assert exit_code == (0 if skipped_count == 3 or worker_status == "published" else 1)
    assert posts == ["FAQ-01", "FAQ-02", "FAQ-03"]
    assert polls == [f"/api/v1/knowledge/documents/FAQ-{i:02d}" for i in range(skipped_count + 1, 4)]
    out = capsys.readouterr().out
    assert f"Đã có sẵn: {skipped_count} | Nạp mới: {3 - skipped_count}" in out
    if skipped_count < 3:
        assert f"{worker_status}: {3 - skipped_count}" in out
    else:
        assert "Đang đợi worker" not in out
        assert "published:" not in out
    manifest = json.loads(next(tmp_path.glob("faq_ingest_*.json")).read_text(encoding="utf-8"))
    documents = manifest["documents"]
    assert len(documents) == 3
    for i in range(1, 4):
        result = documents[f"FAQ-{i:02d}"]
        assert result["skipped"] is (i <= skipped_count)
        assert result["final_status"] == ("already_exists" if i <= skipped_count else worker_status)
        if i <= skipped_count:
            expected_reason = "DOCUMENT_METADATA_CONFLICT" if existing_status == 409 else "DOCUMENT_ALREADY_EXISTS"
            assert result["skip_reason"] == expected_reason


@pytest.mark.parametrize("field", [*ingest_faq.REQUIRED_FIELDS, "additional_sources"])
def test_each_required_faq_field_is_checked(tmp_path, field):
    _, items = ingest_faq.load_faqs(ingest_faq.DEFAULT_SOURCE)
    item = {k: v for k, v in items[0].items() if k != field}
    source = tmp_path / "faq.json"
    source.write_text(json.dumps({"faqs": [item]}), encoding="utf-8")
    with pytest.raises(SystemExit, match=field):
        ingest_faq.load_faqs(source)


def test_dry_run_sends_nothing(capsys):
    assert ingest_faq.main(["--dry-run", "--limit", "3"]) == 0
    out = capsys.readouterr().out
    assert "3 FAQ" in out and "chưa gửi" in out


def test_direct_script_dry_run_without_pythonpath():
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "scripts/ingest_faq.py", "--dry-run", "--limit", "1"],
        cwd=ingest_faq.AI_SERVICE_DIR, env=env, capture_output=True,
        text=True, encoding="utf-8", timeout=30, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "1 FAQ" in result.stdout and "chưa gửi" in result.stdout


@pytest.mark.parametrize("outcome, expected_status", [
    ("new", 202),
    ("existing", 200),
    ("DOCUMENT_METADATA_CONFLICT", 409),
    ("IDEMPOTENCY_KEY_REUSED", 409),
])
def test_upload_matches_actual_knowledge_route_contract(outcome, expected_status):
    from app.infrastructure.knowledge.postgres_knowledge_repository import DocumentConflict
    from app.presentation.api.v1.endpoints import route_knowledge

    data, items = ingest_faq.load_faqs(ingest_faq.DEFAULT_SOURCE)
    item = items[0]
    document = SimpleNamespace(
        id=ingest_faq.logical_id("contract-document"),
        logical_document_id=ingest_faq.logical_id(item["id"]),
        version_no=1, title=item["source_name"], source_url=item["source_url"],
        review_status="approved", is_active=True, error_code=None,
        ingestion_status="queued" if outcome == "new" else "published",
    )

    class FakeUpload:
        async def execute(self, command):
            if outcome not in {"new", "existing"}:
                raise DocumentConflict(outcome)
            return SimpleNamespace(document=document, created=outcome == "new")

    app = FastAPI()
    app.include_router(route_knowledge.router, prefix="/api/v1")
    app.dependency_overrides[route_knowledge.require_admin_api_key] = lambda: None
    app.dependency_overrides[route_knowledge.get_upload_use_case] = lambda: FakeUpload()
    reviewed_at = "2026-11-26T10:00:00+07:00"
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/knowledge/documents",
            data={"metadata": json.dumps(ingest_faq.build_metadata(item, "reviewer", reviewed_at))},
            files={"file": ("FAQ-01.md", ingest_faq.build_markdown(item, data["disclaimer"]), "text/markdown")},
        )
        assert response.status_code == expected_status
        if expected_status == 409:
            assert response.json() == {"detail": outcome}
        else:
            assert response.json()["document_id"] == str(document.id)

        if outcome == "IDEMPOTENCY_KEY_REUSED":
            with pytest.raises(SystemExit, match="FAQ-01: HTTP 409"):
                ingest_faq.upload(client, item, data["disclaimer"], "reviewer", reviewed_at)
        else:
            result = ingest_faq.upload(client, item, data["disclaimer"], "reviewer", reviewed_at)
            assert result["skipped"] is (outcome != "new")
            if outcome == "DOCUMENT_METADATA_CONFLICT":
                assert result["skip_reason"] == outcome


@pytest.mark.parametrize("argv, message", [
    ([], "--reviewed-by"),
    (["--reviewed-by", "Minh Khoa", "--reviewed-at", "2026-11-13T20:00:00"], "múi giờ"),
])
def test_real_run_requires_reviewer_and_timezone(monkeypatch, argv, message):
    monkeypatch.setattr(ingest_faq, "get_settings", lambda: type("Settings", (), {"admin_api_key": "test-admin-key"})())
    with pytest.raises(SystemExit, match=message):
        ingest_faq.main(argv)
