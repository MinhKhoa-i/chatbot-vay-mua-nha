import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from openai import AsyncOpenAI

from app.application.services.chat_response_policy import ChatResponsePolicy
from app.application.services.retrieval_query import RetrievalQueryBuilder
from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.knowledge_evidence import GroundedContext
from app.domain.ports.prompt_catalog import PromptName
from app.domain.services.chat_intent_classifier import ChatIntentClassifier
from app.infrastructure.llm.openai_chat_adapter import OpenAIChatAdapter
from app.infrastructure.prompts.loader import MarkdownPromptCatalog, PromptLoadError, get_prompt_catalog


@pytest.mark.parametrize("name", list(PromptName))
def test_all_packaged_prompts_load_as_nonempty_markdown(name):
    assert get_prompt_catalog().get(name).strip()


def test_loading_is_utf8_cached_and_independent_of_working_directory(tmp_path, monkeypatch):
    path = tmp_path / "greeting.md"
    path.write_text("﻿Xin chào từ Markdown!\n", encoding="utf-8")
    catalog = MarkdownPromptCatalog(tmp_path)
    monkeypatch.chdir(tmp_path.parent)
    assert catalog.get(PromptName.GREETING) == "Xin chào từ Markdown!"
    path.write_text("Đã đổi", encoding="utf-8")
    assert catalog.get(PromptName.GREETING) == "Xin chào từ Markdown!"
    assert MarkdownPromptCatalog(tmp_path).get(PromptName.GREETING) == "Đã đổi"


def test_default_catalog_is_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert "vay mua nhà" in MarkdownPromptCatalog().get(PromptName.CHAT_SYSTEM)


@pytest.mark.parametrize("content", [None, "  \n", b"\xff\xfe\xff"])
def test_missing_empty_or_invalid_utf8_prompt_fails_clearly(tmp_path, content):
    if content is not None:
        path = tmp_path / "greeting.md"
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    with pytest.raises(PromptLoadError, match="greeting"):
        MarkdownPromptCatalog(tmp_path).get(PromptName.GREETING)


def test_unknown_resource_name_cannot_read_arbitrary_files(tmp_path):
    with pytest.raises(ValueError):
        MarkdownPromptCatalog(tmp_path).get("../secret")


def test_application_uses_injected_text_not_infrastructure_imports():
    class InMemoryPrompts:
        def get(self, name):
            return {
                PromptName.GREETING: "CUSTOM HELLO",
                PromptName.THANKS: "CUSTOM THANKS",
                PromptName.FAREWELL: "CUSTOM BYE",
                PromptName.NO_EVIDENCE: "CUSTOM FALLBACK",
                PromptName.RETRIEVAL_GUIDANCE: "CUSTOM GUIDANCE",
                PromptName.RETRIEVAL_QUERY: "{previous_questions}\nCURRENT={text}",
            }[name]

    prompts = InMemoryPrompts()
    policy = ChatResponsePolicy(prompts)
    empty = GroundedContext((), "", ())
    for text, expected in [("Xin chào", "CUSTOM HELLO"), ("Cảm ơn", "CUSTOM THANKS"), ("Tạm biệt", "CUSTOM BYE")]:
        assert policy.deterministic_reply(ChatIntent.GENERAL, text, empty) == expected
    assert policy.deterministic_reply(ChatIntent.RETRIEVAL, "Hồ sơ?", empty) == "CUSTOM FALLBACK"
    assert policy.retrieval_guidance == "CUSTOM GUIDANCE"
    query = RetrievalQueryBuilder(ChatIntentClassifier(), prompts).build(
        "Còn bên đó?", (("user", "Ngân hàng A?"),),
    )
    assert query == "Ngân hàng A?\nCURRENT=Còn bên đó?"


def test_adapter_renders_markdown_templates_without_reformatting_user_content(tmp_path):
    (tmp_path / "chat_system.md").write_text("CUSTOM SYSTEM", encoding="utf-8")
    (tmp_path / "turn_guidance.md").write_text("GUIDANCE={guidance}", encoding="utf-8")
    (tmp_path / "grounding.md").write_text("SOURCES={knowledge_context}", encoding="utf-8")
    requests = []

    async def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=(
            b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\n'
            b'data: [DONE]\n\n'
        ))

    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        adapter = OpenAIChatAdapter(
            base_url="http://provider.test/v1", api_key="test-key", model="test-model",
            prompts=MarkdownPromptCatalog(tmp_path),
        )
        with patch("app.infrastructure.llm.openai_chat_adapter.AsyncOpenAI", side_effect=lambda **kwargs: AsyncOpenAI(
            **kwargs, http_client=client,
        )):
            fragments = [part async for part in adapter.stream_reply(
                "Question {user}", guidance="Do {not} reinterpret", knowledge_context='[1] {"rate": 8}',
            )]
        assert fragments == ["ok"]
        assert requests[0]["messages"][0]["content"] == (
            'CUSTOM SYSTEM\n\nGUIDANCE=Do {not} reinterpret\n\nSOURCES=[1] {"rate": 8}'
        )
        assert requests[0]["messages"][-1]["content"] == "Question {user}"
        await client.aclose()

    asyncio.run(run())
