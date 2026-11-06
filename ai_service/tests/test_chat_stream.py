import asyncio
import json
from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.application.use_cases.stream_chat import StreamChatUseCase
from app.core.config import get_settings
from app.domain.ports.chat_completion import ChatCompletionPort
from app.infrastructure.llm.openai_chat_adapter import ChatProviderUnavailable, OpenAIChatAdapter
from app.presentation.api.chat_dependencies import get_stream_chat_use_case
from app.presentation.api.v1.endpoints.chat import router


class FakeCompletion(ChatCompletionPort):
    def __init__(self, fragments: list[str] | None = None, fail: bool = False) -> None:
        self.fragments = fragments or []
        self.fail = fail
        self.received_text: str | None = None

    async def stream_reply(self, text: str) -> AsyncIterator[str]:
        self.received_text = text
        if self.fail:
            raise ChatProviderUnavailable("private provider details")
        for fragment in self.fragments:
            yield fragment


def make_app(use_case: StreamChatUseCase) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_stream_chat_use_case] = lambda: use_case
    return app


def test_endpoint_streams_sse_deltas_and_never_echoes_conversation_id(monkeypatch):
    completion = FakeCompletion(["Xin chào", " bạn"])
    monkeypatch.setattr("app.presentation.api.v1.endpoints.chat.get_settings", lambda: get_settings().model_copy(update={
        "llm_base_url": "http://provider.test/v1", "llm_api_key": "test-key"
    }))

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app(StreamChatUseCase(completion))),
                                     base_url="http://test") as client:
            conversation_id = uuid4()
            response = await client.post(f"/api/v1/conversations/{conversation_id}/messages", json={
                "client_request_id": str(uuid4()), "text": "Xin chào", "expected_version": 0,
            })
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            assert response.headers["cache-control"] == "no-store"
            assert 'event: delta\ndata: {"text": "Xin chào"}' in response.text
            assert 'event: delta\ndata: {"text": " bạn"}' in response.text
            assert 'event: done\ndata: {"status": "completed"}' in response.text
            assert str(conversation_id) not in response.text
            assert completion.received_text == "Xin chào"

    asyncio.run(run())


def test_endpoint_rejects_extra_fields_and_missing_provider_configuration(monkeypatch):
    completion = FakeCompletion(["ok"])
    monkeypatch.setattr("app.presentation.api.v1.endpoints.chat.get_settings", lambda: get_settings().model_copy(update={
        "llm_base_url": "", "llm_api_key": ""
    }))

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app(StreamChatUseCase(completion))),
                                     base_url="http://test") as client:
            path = f"/api/v1/conversations/{uuid4()}/messages"
            invalid = await client.post(path, json={"client_request_id": str(uuid4()), "text": "hi", "unknown": 1})
            missing_config = await client.post(path, json={"client_request_id": str(uuid4()), "text": "hi"})
            assert invalid.status_code == 422
            assert missing_config.status_code == 503
            assert missing_config.json()["detail"] == "MODEL_UNAVAILABLE"

    asyncio.run(run())


def test_provider_error_is_sanitized_in_stream(monkeypatch):
    completion = FakeCompletion(fail=True)
    monkeypatch.setattr("app.presentation.api.v1.endpoints.chat.get_settings", lambda: get_settings().model_copy(update={
        "llm_base_url": "http://provider.test/v1", "llm_api_key": "test-key"
    }))

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app(StreamChatUseCase(completion))),
                                     base_url="http://test") as client:
            response = await client.post(f"/api/v1/conversations/{uuid4()}/messages", json={
                "client_request_id": str(uuid4()), "text": "hi",
            })
            assert response.status_code == 200
            assert '"code": "MODEL_UNAVAILABLE"' in response.text
            assert "private provider details" not in response.text
            assert "event: done" not in response.text

    asyncio.run(run())


def test_openai_adapter_calls_compatible_endpoint_and_yields_real_http_sse_chunks():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.path == "/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == "cx/gpt-5.6-sol"
        assert body["stream"] is True
        assert body["messages"][-1] == {"role": "user", "content": "Xin chào"}
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=(
            b'data: {"choices":[{"delta":{"content":"Xin"}}]}\n\n'
            + 'data: {"choices":[{"delta":{"content":" chào"}}]}\n\n'.encode("utf-8")
            + b'data: [DONE]\n\n'
        ))

    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        adapter = OpenAIChatAdapter(base_url="http://provider.test/v1", api_key="test-key",
                                    model="cx/gpt-5.6-sol")
        # Injecting the transport exercises SDK URL construction, JSON serialization and SSE parsing.
        from unittest.mock import patch
        with patch("app.infrastructure.llm.openai_chat_adapter.AsyncOpenAI", side_effect=lambda **kwargs: __import__(
            "openai"
        ).AsyncOpenAI(**kwargs, http_client=client)):
            fragments = [fragment async for fragment in adapter.stream_reply("Xin chào")]
        await client.aclose()
        assert fragments == ["Xin", " chào"]
        assert len(requests) == 1
        assert requests[0].headers["authorization"] == "Bearer test-key"

    asyncio.run(run())
