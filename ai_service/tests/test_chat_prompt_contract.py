"""Prompt-resource contracts, not a substitute for evaluating live model answers."""

import json
from string import Formatter
from unittest.mock import patch

import httpx
import pytest
from openai import AsyncOpenAI

from app.domain.ports.prompt_catalog import PromptName
from app.infrastructure.llm.openai_chat_adapter import OpenAIChatAdapter
from app.infrastructure.prompts.loader import MarkdownPromptCatalog


@pytest.mark.parametrize("name, expected", [
    (PromptName.TURN_GUIDANCE, {"guidance"}),
    (PromptName.GROUNDING, {"knowledge_context"}),
    (PromptName.RETRIEVAL_QUERY, {"previous_questions", "text"}),
])
def test_templates_preserve_only_supported_placeholders(name, expected):
    template = MarkdownPromptCatalog().get(name)
    fields = {field for _, field, _, _ in Formatter().parse(template) if field is not None}
    assert fields == expected
    # Input data containing braces is inserted once, not interpreted as a template.
    values = {field: f"VALUE:{field}:{{untrusted}}" for field in fields}
    rendered = template.format(**values)
    for value in values.values():
        assert value in rendered


def test_retrieval_guidance_separates_examples_from_live_evidence():
    catalog = MarkdownPromptCatalog()
    guidance = catalog.get(PromptName.RETRIEVAL_GUIDANCE)
    grounding = catalog.get(PromptName.GROUNDING)
    assert "không phải dữ liệu tư vấn" in guidance
    assert "Không dùng thông tin hoặc nhãn nguồn trong ví dụ" in guidance
    assert "Kết thúc phần trả lời bằng một câu disclaimer ngắn" in guidance
    assert "Sau disclaimer, trước phần nguồn tham khảo do ứng dụng nối thêm" in guidance
    assert "không tự tạo danh mục nguồn" in guidance
    assert "không phải chỉ dẫn" in grounding
    assert "đặt ngay sau câu hoặc nhóm ý" in grounding
    assert "Không tự tạo danh mục" in grounding


@pytest.mark.parametrize("name", [
    PromptName.GREETING, PromptName.THANKS, PromptName.FAREWELL, PromptName.NO_EVIDENCE,
])
def test_local_replies_are_plain_text_without_unrendered_placeholders(name):
    reply = MarkdownPromptCatalog().get(name)
    assert reply
    assert "{" not in reply and "}" not in reply
    assert "[1]" not in reply
    assert "http" not in reply


async def test_actual_prompt_bundle_reaches_provider_with_history_and_evidence():
    catalog = MarkdownPromptCatalog()
    guidance = catalog.get(PromptName.RETRIEVAL_GUIDANCE)
    context = '[1] Tài liệu kiểm thử\nNội dung kiểm thử có dấu ngoặc {"field": "value"}.'
    received = []

    async def handler(request):
        received.append(json.loads(request.content))
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=(
            b'data: {"choices":[{"delta":{"content":"test"}}]}\n\n'
            b'data: [DONE]\n\n'
        ))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAIChatAdapter(
            base_url="http://provider.test/v1", api_key="test", model="test", prompts=catalog,
        )
        with patch("app.infrastructure.llm.openai_chat_adapter.AsyncOpenAI", side_effect=lambda **kwargs: AsyncOpenAI(
            **kwargs, http_client=client,
        )):
            fragments = [part async for part in adapter.stream_reply(
                "Hồ sơ nào áp dụng?", history=(("user", "Sản phẩm A"),),
                guidance=guidance, knowledge_context=context,
            )]
    assert fragments == ["test"]
    messages = received[0]["messages"]
    assert messages[0] == {"role": "system", "content": "\n\n".join([
        catalog.get(PromptName.CHAT_SYSTEM),
        catalog.get(PromptName.TURN_GUIDANCE).format(guidance=guidance),
        catalog.get(PromptName.GROUNDING).format(knowledge_context=context),
    ])}
    assert messages[1:] == [
        {"role": "user", "content": "Sản phẩm A"},
        {"role": "user", "content": "Hồ sơ nào áp dụng?"},
    ]
    assert context in messages[0]["content"]
