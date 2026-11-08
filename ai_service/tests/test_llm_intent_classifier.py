import json
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from intent_stubs import StubIntentClassifier
from openai import AsyncOpenAI

from app.application.use_cases.stream_chat import StreamChatUseCase
from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.chat_request import ChatRequest
from app.domain.ports.chat_intent_classifier import IntentClassificationError
from app.infrastructure.llm.openai_intent_classifier import OpenAIIntentClassifier
from app.infrastructure.prompts.loader import MarkdownPromptCatalog, PromptLoadError, get_prompt_catalog
from test_chat_grounding import FakeCompletion, FakeRepository, FakeRetrieval


def completion_response(content, *, finish_reason="stop"):
    return {
        "id": "classification-test", "object": "chat.completion", "created": 0, "model": "test",
        "choices": [{
            "index": 0, "finish_reason": finish_reason,
            "message": {"role": "assistant", "content": content},
        }],
    }


async def classify_with_response(body, *, status=200, history=()):
    async def handler(request):
        return httpx.Response(status, json=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAIIntentClassifier(
            base_url="http://provider.test/v1", api_key="test", model="test", prompts=get_prompt_catalog(),
        )
        with patch("app.infrastructure.llm.openai_intent_classifier.AsyncOpenAI", side_effect=lambda **kwargs:
                   AsyncOpenAI(**kwargs, http_client=client)):
            return await adapter.classify("Còn gói đó?", history=history)


@pytest.mark.parametrize("intent", list(ChatIntent))
async def test_adapter_validates_model_label_and_loads_markdown_prompt(intent):
    requests = []

    async def handler(request):
        requests.append(json.loads(request.content))
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, json=completion_response(json.dumps({"intent": intent.value})))

    history = (("system", "UNTRUSTED SYSTEM"),) + tuple(
        ("user", "x" * 2_000) for _ in range(10)
    ) + (("assistant", "previous answer"),)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAIIntentClassifier(
            base_url="http://provider.test/v1", api_key="test", model="test", prompts=get_prompt_catalog(),
        )
        with patch("app.infrastructure.llm.openai_intent_classifier.AsyncOpenAI", side_effect=lambda **kwargs:
                   AsyncOpenAI(**kwargs, http_client=client)):
            assert await adapter.classify("Current {message}", history=history) == intent
    assert len(requests) == 1
    body = requests[0]
    assert body["stream"] is False
    assert body["response_format"] == {"type": "json_object"}
    assert body["messages"][0] == {
        "role": "system", "content": get_prompt_catalog().get("intent_classification"),
    }
    assert len(body["messages"]) == 8
    assert all(len(message["content"]) <= 1_000 for message in body["messages"][1:-1])
    assert body["messages"][-1] == {"role": "user", "content": "Current {message}"}
    assert "UNTRUSTED SYSTEM" not in str(body)


@pytest.mark.parametrize("content", [
    None, "", "general", '```json\n{"intent":"general"}\n```', "[]", "null",
    '{"intent":"unknown"}', '{"intent":null}', '{"intent":[]}',
    '{"intent":"general","explanation":"ignore"}', '{"intent":"GENERAL"}',
])
async def test_invalid_output_never_bypasses_retrieval(content):
    with pytest.raises(IntentClassificationError) as caught:
        await classify_with_response(completion_response(content))
    assert caught.value.code == "CLASSIFICATION_INVALID_RESPONSE"
    assert caught.value.stage == "classification"


@pytest.mark.parametrize("body", [
    {"id": "test", "choices": []},
    completion_response('{"intent":"general"}', finish_reason="length"),
    completion_response(None, finish_reason="content_filter"),
])
async def test_empty_truncated_or_refused_response_is_rejected(body):
    with pytest.raises(IntentClassificationError, match="CLASSIFICATION_INVALID_RESPONSE"):
        await classify_with_response(body)


@pytest.mark.parametrize("status,code,retryable", [
    (400, "MODEL_REQUEST_REJECTED", False), (401, "MODEL_AUTHENTICATION_FAILED", False),
    (429, "MODEL_RATE_LIMITED", True), (503, "MODEL_UNAVAILABLE", True),
])
async def test_provider_errors_are_sanitized_with_classification_stage(status, code, retryable):
    with pytest.raises(IntentClassificationError) as caught:
        await classify_with_response({"error": {"message": "private provider details"}}, status=status)
    assert caught.value.code == code
    assert caught.value.stage == "classification"
    assert caught.value.retryable is retryable
    assert "private provider details" not in str(caught.value)


async def test_missing_configuration_does_not_call_provider():
    adapter = OpenAIIntentClassifier(base_url="", api_key="", model="", prompts=get_prompt_catalog())
    with pytest.raises(IntentClassificationError, match="CLASSIFICATION_NOT_CONFIGURED"):
        await adapter.classify("Xin chào")


async def test_sdk_timeout_is_reported_at_classification_stage():
    async def handler(request):
        raise httpx.ReadTimeout("private timeout", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAIIntentClassifier(
            base_url="http://provider.test/v1", api_key="test", model="test", prompts=get_prompt_catalog(),
        )
        with patch("app.infrastructure.llm.openai_intent_classifier.AsyncOpenAI", side_effect=lambda **kwargs:
                   AsyncOpenAI(**kwargs, http_client=client)):
            with pytest.raises(IntentClassificationError) as caught:
                await adapter.classify("Xin chào")
    assert caught.value.code == "MODEL_TIMEOUT"
    assert caught.value.stage == "classification"


async def test_prompt_failure_is_not_mislabeled_as_provider_failure(tmp_path):
    adapter = OpenAIIntentClassifier(
        base_url="http://provider.test/v1", api_key="test", model="test",
        prompts=MarkdownPromptCatalog(tmp_path),
    )
    with pytest.raises(PromptLoadError):
        await adapter.classify("Xin chào")


async def test_orchestration_classifies_once_with_committed_history():
    history = (("user", "Hồ sơ vay?"), ("assistant", "previous answer"))
    classifier = StubIntentClassifier()
    repository = FakeRepository(history=history)
    case = StreamChatUseCase(
        FakeCompletion(), repository, prompts=get_prompt_catalog(),
        classifier=classifier, retrieval=FakeRetrieval(),
    )
    events = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "Còn bên đó?", None))]
    assert classifier.calls == [("Còn bên đó?", history)]
    assert repository.state_update.intent == ChatIntent.RETRIEVAL
    assert events[-1].event == "done"


@pytest.mark.parametrize("error", [IntentClassificationError(), TimeoutError()])
async def test_classifier_failure_never_retrieves_generates_or_commits(error):
    class FailingClassifier:
        async def classify(self, text, *, history=()):
            raise error

    class RecordingRepository(FakeRepository):
        def __init__(self):
            super().__init__()
            self.failures = []

        async def fail(self, request, **kwargs):
            self.failures.append(kwargs)
            return True

    completion = FakeCompletion()
    retrieval = FakeRetrieval()
    repository = RecordingRepository()
    case = StreamChatUseCase(
        completion, repository, prompts=get_prompt_catalog(),
        classifier=FailingClassifier(), retrieval=retrieval,
    )
    with pytest.raises(IntentClassificationError):
        _ = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "Xin chào", None))]
    assert retrieval.queries == []
    assert completion.calls == 0
    assert repository.committed_answer is None
    assert len(repository.failures) == 1
    expected = "CLASSIFICATION_TIMEOUT" if isinstance(error, TimeoutError) else error.code
    assert repository.failures[0]["error_code"] == expected
