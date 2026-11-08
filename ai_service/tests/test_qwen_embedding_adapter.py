import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from openai import APIConnectionError

from app.infrastructure.knowledge.qwen_embedding_adapter import EmbeddingUnavailable, QwenEmbeddingAdapter


def adapter():
    return QwenEmbeddingAdapter(base_url="http://localhost:20128/v1", api_key="any-string",
                                model="local-qwen", dimensions=2, source_dimensions=4)


def row(index, values):
    return SimpleNamespace(index=index, embedding=values)


def mock_client():
    client = AsyncMock()
    client.__aenter__.return_value = client
    return client


def test_sdk_receives_configuration_and_batches_in_original_order():
    client = mock_client()
    client.embeddings.create.side_effect = [
        SimpleNamespace(data=[row(i, [3.0, 4.0, 0.0, 0.0]) for i in reversed(range(32))]),
        SimpleNamespace(data=[row(0, [0.0, 2.0, 0.0, 0.0])]),
    ]
    texts = [f"chunk-{i}" for i in range(33)]
    with patch("app.infrastructure.knowledge.qwen_embedding_adapter.AsyncOpenAI", return_value=client) as factory:
        vectors = asyncio.run(adapter().embed_documents(texts))
    factory.assert_called_once_with(base_url="http://localhost:20128/v1", api_key="any-string",
                                    timeout=30.0, max_retries=2)
    assert client.embeddings.create.await_args_list[0].kwargs == {
        "model": "local-qwen", "input": texts[:32], "encoding_format": "float",
    }
    assert client.embeddings.create.await_args_list[1].kwargs["input"] == texts[32:]
    assert vectors == [[0.6, 0.8]] * 32 + [[0.0, 1.0]]
    client.__aexit__.assert_awaited_once()


@pytest.mark.parametrize("rows", [
    [],
    [row(1, [1.0, 0.0, 0.0, 0.0])],
    [row(0, [1.0])],
    [row(0, [0.0, 0.0, 1.0, 0.0])],
    [row(0, [float("nan"), 1.0, 0.0, 0.0])],
])
def test_invalid_vectors_are_rejected(rows):
    client = mock_client()
    client.embeddings.create.return_value = SimpleNamespace(data=rows)
    with patch("app.infrastructure.knowledge.qwen_embedding_adapter.AsyncOpenAI", return_value=client):
        with pytest.raises(EmbeddingUnavailable):
            asyncio.run(adapter().embed_documents(["chunk"]))


def test_sdk_connection_error_is_mapped_to_domain_adapter_error():
    import httpx

    client = mock_client()
    client.embeddings.create.side_effect = APIConnectionError(request=httpx.Request("POST", "http://example.test/v1/embeddings"))
    with patch("app.infrastructure.knowledge.qwen_embedding_adapter.AsyncOpenAI", return_value=client):
        with pytest.raises(EmbeddingUnavailable, match="provider unavailable"):
            asyncio.run(adapter().embed_documents(["chunk"]))


def test_empty_input_does_not_create_sdk_client():
    with patch("app.infrastructure.knowledge.qwen_embedding_adapter.AsyncOpenAI") as factory:
        assert asyncio.run(adapter().embed_documents([])) == []
    factory.assert_not_called()
