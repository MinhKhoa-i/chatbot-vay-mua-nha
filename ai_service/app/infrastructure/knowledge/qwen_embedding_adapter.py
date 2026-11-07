import math

from openai import APIError, AsyncOpenAI


from app.domain.errors import RetrievalError


class EmbeddingUnavailable(RetrievalError):
    def __init__(self, message: str, *, code: str = "EMBEDDING_UNAVAILABLE", retryable: bool = True) -> None:
        super().__init__(code, stage="embedding", retryable=retryable)
        self.args = (message,)


class QwenEmbeddingAdapter:
    def __init__(self, *, base_url: str, api_key: str, model: str = "qwen/qwen3-embedding-8b",
                 dimensions: int = 1536, source_dimensions: int = 4096, timeout_seconds: float = 30.0) -> None:
        if not 0 < dimensions <= source_dimensions:
            raise ValueError("embedding dimensions must be between 1 and source_dimensions")
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._source_dimensions = source_dimensions
        self._timeout = timeout_seconds

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._base_url or not self._api_key:
            raise EmbeddingUnavailable("embedding provider is not configured", code="EMBEDDING_NOT_CONFIGURED", retryable=False)
        vectors: list[list[float]] = []
        try:
            async with AsyncOpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
                timeout=self._timeout,
                max_retries=2,
            ) as client:
                for offset in range(0, len(texts), 32):
                    batch = texts[offset : offset + 32]
                    response = await client.embeddings.create(
                        model=self._model,
                        input=batch,
                        encoding_format="float",
                    )
                    rows = sorted(response.data, key=lambda item: item.index)
                    if [row.index for row in rows] != list(range(len(batch))):
                        raise EmbeddingUnavailable("embedding response count or indexes mismatch")
                    if any(len(row.embedding) != self._source_dimensions for row in rows):
                        raise EmbeddingUnavailable("embedding response dimension mismatch")
                    vectors.extend(self._normalize(row.embedding[: self._dimensions]) for row in rows)
        except APIError as exc:
            raise EmbeddingUnavailable("embedding provider unavailable or rejected request") from exc
        except (AttributeError, TypeError, ValueError) as exc:
            raise EmbeddingUnavailable("embedding provider returned invalid response") from exc
        return vectors

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        if any(not math.isfinite(float(value)) for value in vector):
            raise EmbeddingUnavailable("embedding contains non-finite values")
        norm = math.sqrt(sum(float(value) ** 2 for value in vector))
        if norm == 0 or not math.isfinite(norm):
            raise EmbeddingUnavailable("invalid zero or non-finite embedding")
        return [float(value) / norm for value in vector]
