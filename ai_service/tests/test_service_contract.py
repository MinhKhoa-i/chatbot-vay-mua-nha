"""Regression checks for the documented service entry point and capabilities."""

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.domain.ports.prompt_catalog import PromptName
from app.infrastructure.prompts.loader import MarkdownPromptCatalog


SERVICE_ROOT = Path(__file__).resolve().parents[1]


def test_app_imports_from_service_directory_without_repository_on_pythonpath():
    # Uvicorn runs from ai_service/, where the parent package ai_service is absent.
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", "from app.main import app; assert app.title"],
        cwd=SERVICE_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_app_lifespan_and_public_routes_without_external_services(monkeypatch):
    from app import main

    initialize_database = Mock()
    dispose_database = AsyncMock()
    monkeypatch.setattr(main, "get_async_session_factory", initialize_database)
    monkeypatch.setattr(main, "dispose_database", dispose_database)

    with TestClient(main.app) as client:
        initialize_database.assert_called_once_with()
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        paths = client.get("/openapi.json").json()["paths"]
        assert "post" in paths["/api/v1/conversations"]
        assert "post" in paths["/api/v1/conversations/{conversation_id}/messages"]
        assert "post" in paths["/api/v1/knowledge/documents"]
        assert "get" in paths["/api/v1/knowledge/documents/{document_id}"]
        assert "patch" in paths["/api/v1/knowledge/documents/{document_id}/activation"]

    dispose_database.assert_awaited_once_with()


def test_knowledge_routes_require_admin_api_key(monkeypatch):
    from app import main
    from app.presentation.api import knowledge_dependencies

    monkeypatch.setattr(main, "get_async_session_factory", Mock())
    monkeypatch.setattr(main, "dispose_database", AsyncMock())

    document_id = uuid4()
    document = SimpleNamespace(
        id=document_id,
        logical_document_id=uuid4(),
        version_no=1,
        title="FAQ",
        source_url=None,
        review_status="approved",
        ingestion_status="published",
        is_active=True,
        error_code=None,
    )

    class FakeUpload:
        async def execute(self, command):
            return SimpleNamespace(document=document, created=True)

    class FakeReader:
        async def execute(self, requested_id):
            return document if requested_id == document_id else None

    class FakeActivation:
        async def execute(self, requested_id, is_active):
            return document if requested_id == document_id else None

    main.app.dependency_overrides[knowledge_dependencies.get_upload_use_case] = lambda: FakeUpload()
    main.app.dependency_overrides[knowledge_dependencies.get_document_reader] = lambda: FakeReader()
    main.app.dependency_overrides[knowledge_dependencies.get_document_activation_updater] = lambda: FakeActivation()
    monkeypatch.setattr(knowledge_dependencies, "get_settings", lambda: SimpleNamespace(admin_api_key="expected-key"))

    try:
        with TestClient(main.app) as client:
            missing = client.get(f"/api/v1/knowledge/documents/{document_id}")
            wrong = client.get(f"/api/v1/knowledge/documents/{document_id}", headers={"X-Admin-Key": "wrong-key"})
            valid = client.get(f"/api/v1/knowledge/documents/{document_id}", headers={"X-Admin-Key": "expected-key"})
            activation = client.patch(
                f"/api/v1/knowledge/documents/{document_id}/activation",
                headers={"X-Admin-Key": "expected-key"},
                json={"is_active": False},
            )
            upload = client.post(
                "/api/v1/knowledge/documents",
                headers={"X-Admin-Key": "expected-key"},
                data={
                    "metadata": '{"title":"FAQ","verified":true,"reviewed_by":"reviewer",'
                    '"reviewed_at":"2026-11-20T00:00:00+00:00"}',
                },
                files={"file": ("faq.md", b"# FAQ", "text/markdown")},
            )

        assert missing.status_code == 401
        assert missing.json() == {"detail": "ADMIN_AUTHENTICATION_REQUIRED"}
        assert wrong.status_code == 401
        assert valid.status_code == 200
        assert activation.status_code == 200
        assert upload.status_code == 202
    finally:
        main.app.dependency_overrides.clear()


def test_empty_admin_api_key_rejects_knowledge_routes(monkeypatch):
    from app import main
    from app.presentation.api import knowledge_dependencies

    monkeypatch.setattr(main, "get_async_session_factory", Mock())
    monkeypatch.setattr(main, "dispose_database", AsyncMock())
    monkeypatch.setattr(knowledge_dependencies, "get_settings", lambda: SimpleNamespace(admin_api_key=""))

    with TestClient(main.app) as client:
        response = client.get(f"/api/v1/knowledge/documents/{uuid4()}", headers={"X-Admin-Key": "any-key"})

    assert response.status_code == 503
    assert response.json() == {"detail": "ADMIN_API_KEY_NOT_CONFIGURED"}


def test_chat_route_remains_public_without_admin_api_key(monkeypatch):
    from app import main
    from app.presentation.api.chat_dependencies import get_stream_chat_use_case

    class FakeChatUseCase:
        async def execute(self, request):
            yield SimpleNamespace(event="done", data={"status": "completed"})

    monkeypatch.setattr(main, "get_async_session_factory", Mock())
    monkeypatch.setattr(main, "dispose_database", AsyncMock())
    main.app.dependency_overrides[get_stream_chat_use_case] = lambda: FakeChatUseCase()

    try:
        with TestClient(main.app) as client:
            response = client.post(
                f"/api/v1/conversations/{uuid4()}/messages",
                json={"client_request_id": str(uuid4()), "text": "Xin chào", "expected_version": 0},
            )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'event: done\ndata: {"status": "completed"}' in response.text


def test_app_logger_does_not_duplicate_records_with_root_handler():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import logging; logging.basicConfig(level=logging.INFO); "
            "from app import main; "
            "logging.getLogger('app.infrastructure.llm.usage_logging').info('usage probe')",
        ],
        cwd=SERVICE_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr.count("usage probe") == 1


def test_greeting_does_not_advertise_unimplemented_calculations():
    catalog = MarkdownPromptCatalog()
    guidance = catalog.get(PromptName.GENERAL_GUIDANCE)
    system = catalog.get(PromptName.CHAT_SYSTEM)

    assert "không tự tính toán khoản vay" in guidance
    assert "Không tự tính tiền trả nợ" in system
    assert "kết thúc bằng một câu disclaimer ngắn do bạn viết" in system
    assert "không cần disclaimer này" in system
