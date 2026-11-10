import asyncio
import json
from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
from fastapi import FastAPI

from intent_stubs import StubIntentClassifier

from app.application.use_cases.stream_chat import StreamChatUseCase
from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.chat_request import ChatClaim, ChatCommit, ChatRequest, ChatSnapshot
from app.domain.entities.knowledge_evidence import GroundedContext, KnowledgeEvidence
from app.domain.ports.chat_completion import ChatCompletionPort, ChatProviderUnavailable
from app.domain.ports.chat_turn_repository import ChatTurnRepository
from app.infrastructure.llm.openai_chat_adapter import OpenAIChatAdapter
from app.infrastructure.prompts.loader import get_prompt_catalog
from app.presentation.api.chat_dependencies import get_stream_chat_use_case
from app.presentation.api.v1.endpoints.route_chat import router


class FakeRepository(ChatTurnRepository):
    async def get_conversation_status(self, conversation_id):
        return "active"

    async def claim(self, request: ChatRequest, request_hash: str) -> ChatClaim:
        return ChatClaim("claimed", ChatSnapshot(0, (), uuid4(), uuid4()))

    async def commit(self, request: ChatRequest, *, request_id, lease_token, snapshot_version, answer, state_update=None, estimate=None) -> ChatCommit:
        return ChatCommit({"status": "completed"}, 200, uuid4(), uuid4(), snapshot_version + 1)

    async def fail(self, request: ChatRequest, *, request_id, lease_token, error_code, response_status, retryable) -> bool:
        return True


class FakeCompletion(ChatCompletionPort):
    def __init__(self, fragments: list[str] | None = None, fail: bool = False) -> None:
        self.fragments = fragments or []
        self.fail = fail
        self.received_text: str | None = None
        self.received_history: tuple[tuple[str, str], ...] = ()
        self.received_guidance = ""
        self.received_knowledge_context = ""

    async def stream_reply(
        self, text: str, *, history=(), guidance="", knowledge_context=""
    ) -> AsyncIterator[str]:
        self.received_text = text
        self.received_history = history
        self.received_guidance = guidance
        self.received_knowledge_context = knowledge_context
        if self.fail:
            raise ChatProviderUnavailable("private provider details")
        for fragment in self.fragments:
            yield fragment


class FakeRetrieval:
    async def retrieve(self, text):
        item = KnowledgeEvidence(
            chunk_id=uuid4(), document_id=uuid4(), title="Hồ sơ", source_url=None,
            body="Cần giấy tờ.", score=0.9,
        )
        return GroundedContext((item,), "Cần giấy tờ.", ())


def make_app(use_case: StreamChatUseCase) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_stream_chat_use_case] = lambda: use_case
    return app


def test_endpoint_streams_sse_deltas_and_never_echoes_conversation_id(monkeypatch):
    completion = FakeCompletion(["Xin chào", " bạn"])

    async def run():
        use_case = StreamChatUseCase(
            completion, FakeRepository(), prompts=get_prompt_catalog(),
            classifier=StubIntentClassifier(ChatIntent.GENERAL),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=make_app(use_case)), base_url="http://test",
        ) as client:
            conversation_id = uuid4()
            response = await client.post(f"/api/v1/conversations/{conversation_id}/messages", json={
                "client_request_id": str(uuid4()), "text": "Xin chào", "expected_version": 0,
            })
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            assert response.headers["cache-control"] == "no-store"
            assert 'event: delta\ndata: {"text": "Xin chào!' in response.text
            assert 'event: done\ndata: {"status": "completed"}' in response.text
            assert str(conversation_id) not in response.text
        assert completion.received_text is None

    asyncio.run(run())


def test_endpoint_rejects_extra_fields(monkeypatch):
    completion = FakeCompletion(["ok"])

    async def run():
        use_case = StreamChatUseCase(
            completion, FakeRepository(), prompts=get_prompt_catalog(),
            classifier=StubIntentClassifier(ChatIntent.GENERAL),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=make_app(use_case)), base_url="http://test",
        ) as client:
            path = f"/api/v1/conversations/{uuid4()}/messages"
            invalid = await client.post(path, json={"client_request_id": str(uuid4()), "text": "hi", "unknown": 1})
            assert invalid.status_code == 422

    asyncio.run(run())


def test_provider_error_is_sanitized_in_stream(monkeypatch):
    completion = FakeCompletion(fail=True)
    use_case = StreamChatUseCase(
        completion, FakeRepository(), prompts=get_prompt_catalog(),
        classifier=StubIntentClassifier(), retrieval=FakeRetrieval(),
    )

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app(use_case)),
                                     base_url="http://test") as client:
            response = await client.post(f"/api/v1/conversations/{uuid4()}/messages", json={
                "client_request_id": str(uuid4()), "text": "Hồ sơ vay cần gì?",
            })
            assert response.status_code == 200
            assert '"code": "MODEL_UNAVAILABLE"' in response.text
            assert "private provider details" not in response.text
            assert "event: done" not in response.text

    asyncio.run(run())


def test_retrieval_endpoint_streams_model_fragments_and_commits(monkeypatch):
    completion = FakeCompletion(["Theo tài liệu", ", cần giấy tờ."])
    use_case = StreamChatUseCase(
        completion, FakeRepository(), prompts=get_prompt_catalog(),
        classifier=StubIntentClassifier(), retrieval=FakeRetrieval(),
    )

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app(use_case)),
                                     base_url="http://test") as client:
            response = await client.post(f"/api/v1/conversations/{uuid4()}/messages", json={
                "client_request_id": str(uuid4()), "text": "Chào bạn, hồ sơ vay cần gì?",
            })
            assert response.status_code == 200
            assert 'event: delta\ndata: {"text": "Theo tài liệu"}' in response.text
            assert 'event: delta\ndata: {"text": ", cần giấy tờ."}' in response.text
            assert response.text.index("event: done") > response.text.rindex("event: delta")
            assert completion.received_text == "Chào bạn, hồ sơ vay cần gì?"
            assert completion.received_knowledge_context == "Cần giấy tờ."

    asyncio.run(run())


def test_openai_adapter_calls_compatible_endpoint_and_yields_real_http_sse_chunks():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.path == "/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == "cx/gpt-5.6-sol"
        assert body["stream"] is True
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1:] == [{"role": "user", "content": "Xin chào"}]
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
