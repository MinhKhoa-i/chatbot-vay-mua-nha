import json
from collections import Counter
from uuid import NAMESPACE_URL, uuid5

import httpx
import pytest

from scripts import ingest_faq


def test_repository_faq_file_has_50_entries_in_5_categories():
    data, items = ingest_faq.load_faqs(ingest_faq.DEFAULT_SOURCE)
    assert len(items) == 50
    assert set(Counter(item["category"] for item in items).values()) == {10}
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
    source.write_text(json.dumps({"faqs": faqs}), encoding="utf-8")
    with pytest.raises(SystemExit, match=message):
        ingest_faq.load_faqs(source)


def test_upload_then_wait_until_published():
    polls = Counter()

    def handler(request):
        if request.method == "POST":
            assert request.url.path == "/api/v1/knowledge/documents"
            assert b'"logical_document_id"' in request.content
            return httpx.Response(202, json={"document_id": "d1", "ingestion_status": "queued"})
        polls[request.url.path] += 1
        status = "processing" if polls[request.url.path] < 2 else "published"
        return httpx.Response(200, json={"document_id": "d1", "ingestion_status": status})

    data, items = ingest_faq.load_faqs(ingest_faq.DEFAULT_SOURCE)
    with httpx.Client(base_url="http://ai.test", transport=httpx.MockTransport(handler)) as client:
        result = ingest_faq.upload(
            client, items[0], data["disclaimer"], "Minh Khoa", "2026-11-13T20:00:00+07:00",
        )
        assert result["ingestion_status"] == "queued"
        final = ingest_faq.wait_until_done(client, {items[0]["id"]: "d1"}, timeout=5, sleep=lambda _: None)
    assert final == {items[0]["id"]: "published"}


def test_upload_error_stops_with_faq_id():
    data, items = ingest_faq.load_faqs(ingest_faq.DEFAULT_SOURCE)
    transport = httpx.MockTransport(lambda request: httpx.Response(409, json={"detail": "conflict"}))
    with httpx.Client(base_url="http://ai.test", transport=transport) as client:
        with pytest.raises(SystemExit, match=items[0]["id"]):
            ingest_faq.upload(client, items[0], data["disclaimer"], "Minh Khoa", "2026-11-13T20:00:00+07:00")


def test_dry_run_sends_nothing(capsys):
    assert ingest_faq.main(["--dry-run", "--limit", "3"]) == 0
    out = capsys.readouterr().out
    assert "3 FAQ" in out and "chưa gửi" in out


@pytest.mark.parametrize("argv, message", [
    ([], "--reviewed-by"),
    (["--reviewed-by", "Minh Khoa", "--reviewed-at", "2026-11-13T20:00:00"], "múi giờ"),
])
def test_real_run_requires_reviewer_and_timezone(argv, message):
    with pytest.raises(SystemExit, match=message):
        ingest_faq.main(argv)
