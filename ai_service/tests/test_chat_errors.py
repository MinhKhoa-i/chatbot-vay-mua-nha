from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI, APIStatusError
from sqlalchemy.exc import SQLAlchemyError

from intent_stubs import StubIntentClassifier

from app.application.services.knowledge_retrieval import KnowledgeRetrievalService
from app.application.use_cases.stream_chat import StreamChatUseCase
from app.domain.entities.chat_request import ChatClaim, ChatRequest, ChatSnapshot
from app.domain.entities.knowledge_evidence import GroundedContext, KnowledgeEvidence
from app.domain.errors import ConversationStateError, RetrievalError, UnexpectedChatError
from app.domain.ports.chat_completion import ChatProviderUnavailable
from app.infrastructure.db.chat_error_boundary import chat_repository_errors
from app.infrastructure.llm.openai_chat_adapter import OpenAIChatAdapter
from app.infrastructure.prompts.loader import MarkdownPromptCatalog, PromptLoadError, get_prompt_catalog
from app.presentation.api import chat_dependencies
from app.presentation.api.v1.endpoints.route_chat import router


class Repository:
    def __init__(self, *, claim_error=None, commit_error=None, fail_error=None):
        self.claim_error = claim_error
        self.commit_error = commit_error
        self.fail_error = fail_error
        self.failures = []
        self.commits = 0

    async def claim(self, *args):
        if self.claim_error:
            raise self.claim_error
        return ChatClaim("claimed", ChatSnapshot(0, (), uuid4(), uuid4()))

    async def commit(self, *args, **kwargs):
        self.commits += 1
        if self.commit_error:
            raise self.commit_error
        raise AssertionError("must not successfully commit")

    async def fail(self, *args, **kwargs):
        self.failures.append(kwargs)
        if self.fail_error:
            raise self.fail_error
        return True


class Retrieval:
    async def retrieve(self, text):
        item = KnowledgeEvidence(uuid4(), uuid4(), "Title", None, "Verified context", 0.9)
        return GroundedContext((item,), "Verified context", ())


class Completion:
    def __init__(self, error=None):
        self.error = error

    async def stream_reply(self, *args, **kwargs):
        yield "provisional text"
        if self.error:
            raise self.error


def use_case(repository, *, completion=None, retrieval=None):
    return StreamChatUseCase(
        completion or Completion(), repository, prompts=get_prompt_catalog(),
        retrieval=retrieval or Retrieval(), classifier=StubIntentClassifier(),
    )


def request():
    return ChatRequest(uuid4(), uuid4(), "Hồ sơ vay?", None)


async def collect(case):
    return [event async for event in case.execute(request())]


async def call_endpoint(case):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[chat_dependencies.get_stream_chat_use_case] = lambda: case
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(f"/api/v1/conversations/{uuid4()}/messages", json={
            "client_request_id": str(uuid4()), "text": "Hồ sơ vay?",
        })


async def test_cleanup_failure_does_not_mask_original_model_error(caplog):
    original = ChatProviderUnavailable(code="MODEL_RATE_LIMITED")
    repository = Repository(fail_error=RuntimeError("secondary storage failure"))
    with pytest.raises(ChatProviderUnavailable) as caught:
        await collect(use_case(repository, completion=Completion(original)))
    assert caught.value is original
    assert repository.failures[0]["error_code"] == "MODEL_RATE_LIMITED"
    assert repository.failures[0]["retryable"] is True
    assert repository.commits == 0
    assert "Failed to record chat failure" in caplog.text


async def test_commit_error_is_not_misclassified_as_model_error():
    original = ConversationStateError(stage="commit")
    repository = Repository(commit_error=original)
    response = await call_endpoint(use_case(repository))
    assert "event: delta" in response.text
    assert '"code": "STATE_UNAVAILABLE"' in response.text
    assert "MODEL_UNAVAILABLE" not in response.text
    assert "event: done" not in response.text
    assert repository.failures[0]["error_code"] == original.code


async def test_claim_error_does_not_attempt_to_fail_an_unclaimed_request(caplog):
    repository = Repository(claim_error=ConversationStateError(stage="claim", corrupt=True))
    response = await call_endpoint(use_case(repository))
    assert response.status_code == 200
    assert '"code": "STATE_CORRUPTED", "retryable": false' in response.text
    assert repository.failures == []
    assert "stage=claim" in caplog.text
    assert caplog.records[-1].exc_info is not None


async def test_unexpected_error_keeps_cause_and_correct_stage():
    original = RuntimeError("private internal details")
    repository = Repository(commit_error=original)
    with pytest.raises(UnexpectedChatError) as caught:
        await collect(use_case(repository))
    assert caught.value.stage == "commit"
    assert caught.value.__cause__ is original
    assert caught.value.code == "INTERNAL_ERROR"
    assert caught.value.retryable is False


async def test_endpoint_sanitizes_unexpected_errors():
    repository = Repository(claim_error=RuntimeError("private database URL"))
    response = await call_endpoint(use_case(repository))
    assert '"code": "INTERNAL_ERROR"' in response.text
    assert "private database URL" not in response.text
    assert "event: done" not in response.text


@pytest.mark.parametrize("operation", ["claim", "commit", "fail"])
async def test_repository_boundary_chains_database_errors(operation):
    original = SQLAlchemyError("private database details")

    @chat_repository_errors(operation)
    async def failing():
        raise original

    with pytest.raises(ConversationStateError) as caught:
        await failing()
    assert caught.value.__cause__ is original
    assert caught.value.stage == operation
    assert caught.value.code == "STATE_UNAVAILABLE"
    assert "private database details" not in str(caught.value)


@pytest.mark.parametrize("stage, expected", [("embedding", "EMBEDDING_UNAVAILABLE"), ("search", "KNOWLEDGE_SEARCH_UNAVAILABLE")])
async def test_retrieval_distinguishes_embedding_and_search_failure(stage, expected):
    original = RuntimeError("private upstream details")

    class Embedder:
        async def embed_documents(self, texts):
            if stage == "embedding":
                raise original
            return [[0.1, 0.2]]

    class Knowledge:
        async def search_approved(self, query):
            raise original

    with pytest.raises(RetrievalError) as caught:
        await KnowledgeRetrievalService(Knowledge(), Embedder()).retrieve("question")
    assert caught.value.code == expected
    assert caught.value.__cause__ is original


@pytest.mark.parametrize("status, code, retryable", [
    (400, "MODEL_REQUEST_REJECTED", False),
    (401, "MODEL_AUTHENTICATION_FAILED", False),
    (403, "MODEL_AUTHENTICATION_FAILED", False),
    (429, "MODEL_RATE_LIMITED", True),
    (503, "MODEL_UNAVAILABLE", True),
])
async def test_model_adapter_translates_real_sdk_http_errors(status, code, retryable):
    async def handler(request):
        return httpx.Response(status, json={"error": {"message": "private provider details"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAIChatAdapter(base_url="http://provider.test/v1", api_key="test", model="test")
        with patch("app.infrastructure.llm.openai_chat_adapter.AsyncOpenAI", side_effect=lambda **kwargs: AsyncOpenAI(
            **kwargs, http_client=client,
        )):
            with pytest.raises(ChatProviderUnavailable) as caught:
                _ = [part async for part in adapter.stream_reply("question")]
    assert caught.value.code == code
    assert caught.value.retryable is retryable
    assert isinstance(caught.value.__cause__, APIStatusError)
    assert "private provider details" not in str(caught.value)


async def test_model_configuration_is_checked_at_provider_not_social_route():
    adapter = OpenAIChatAdapter(base_url="", api_key="", model="test")
    with pytest.raises(ChatProviderUnavailable) as caught:
        _ = [part async for part in adapter.stream_reply("question")]
    assert caught.value.code == "MODEL_NOT_CONFIGURED"
    assert caught.value.retryable is False


async def test_sdk_timeout_is_raised_as_model_timeout():
    async def handler(request):
        raise httpx.ReadTimeout("private timeout details", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAIChatAdapter(base_url="http://provider.test/v1", api_key="test", model="test")
        with patch("app.infrastructure.llm.openai_chat_adapter.AsyncOpenAI", side_effect=lambda **kwargs: AsyncOpenAI(
            **kwargs, http_client=client,
        )):
            with pytest.raises(ChatProviderUnavailable) as caught:
                _ = [part async for part in adapter.stream_reply("question")]
    assert caught.value.code == "MODEL_TIMEOUT"
    assert caught.value.retryable is True
    assert caught.value.__cause__ is not None


async def test_unexpected_repository_error_is_logged_and_reraised_unchanged(caplog):
    original = RuntimeError("unexpected failure")

    @chat_repository_errors("claim")
    async def failing():
        raise original

    with pytest.raises(RuntimeError) as caught:
        await failing()
    assert caught.value is original
    assert "operation=claim" in caplog.text
    assert caplog.records[-1].exc_info is not None


def test_invalid_prompt_template_is_raised_at_loader(tmp_path):
    (tmp_path / "grounding.md").write_text("Context: {wrong_field}", encoding="utf-8")
    from app.domain.ports.prompt_catalog import PromptName
    with pytest.raises(PromptLoadError) as caught:
        MarkdownPromptCatalog(tmp_path).get(PromptName.GROUNDING)
    assert isinstance(caught.value.__cause__, KeyError)
    assert caught.value.code == "PROMPT_UNAVAILABLE"
    assert caught.value.stage == "prompt"


def test_prompt_dependency_failure_is_not_reported_as_database_failure(monkeypatch):
    original = PromptLoadError("missing prompt")

    def fail():
        raise original

    monkeypatch.setattr(chat_dependencies, "get_prompt_catalog", fail)
    chat_dependencies.get_stream_chat_use_case.cache_clear()
    try:
        with pytest.raises(HTTPException) as caught:
            chat_dependencies.get_stream_chat_use_case()
        assert caught.value.status_code == 503
        assert caught.value.detail == {"code": "PROMPT_UNAVAILABLE", "retryable": False}
        assert caught.value.__cause__ is original
    finally:
        chat_dependencies.get_stream_chat_use_case.cache_clear()
