"""Regression checks for the documented service entry point and capabilities."""

import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock, Mock

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

    dispose_database.assert_awaited_once_with()


def test_greeting_does_not_advertise_unimplemented_calculations():
    catalog = MarkdownPromptCatalog()
    greeting = catalog.get(PromptName.GREETING)
    system = catalog.get(PromptName.CHAT_SYSTEM)

    assert "gọi backend" in greeting
    assert "lãi suất cố định toàn kỳ" in greeting
    assert "cung cấp và xác nhận" in greeting
    assert "không phải đánh giá khả năng vay theo thu nhập" in greeting
    assert "Không tự tính tiền trả nợ" in system
    assert "công cụ tính toán chưa được tích hợp" not in greeting
