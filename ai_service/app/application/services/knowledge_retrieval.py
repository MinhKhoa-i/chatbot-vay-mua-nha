from app.domain.errors import ChatError, RetrievalError
from app.domain.entities.knowledge_evidence import GroundedContext, KnowledgeSearchQuery
from app.domain.ports.knowledge_ingestion import KnowledgeRepository, TextEmbedder


class KnowledgeRetrievalService:
    """Creates bounded, traceable prompt context from approved knowledge only."""

    def __init__(
        self,
        repository: KnowledgeRepository,
        embedder: TextEmbedder,
        *,
        limit: int = 5,
        min_score: float = 0.15,
        max_context_characters: int = 12_000,
    ) -> None:
        if limit < 1 or max_context_characters < 1:
            raise ValueError("retrieval limits must be positive")
        self._repository = repository
        self._embedder = embedder
        self._limit = limit
        self._min_score = min_score
        self._max_context_characters = max_context_characters

    async def retrieve(self, text: str) -> GroundedContext:
        try:
            vectors = await self._embedder.embed_documents([text])
        except ChatError:
            raise
        except Exception as exc:
            raise RetrievalError("EMBEDDING_UNAVAILABLE", stage="embedding") from exc
        if len(vectors) != 1 or not vectors[0]:
            raise RetrievalError("EMBEDDING_INVALID_RESPONSE", stage="embedding", retryable=False)
        try:
            evidence = await self._repository.search_approved(KnowledgeSearchQuery(
                text=text,
                embedding=tuple(vectors[0]),
                limit=self._limit,
                min_score=self._min_score,
            ))
        except ChatError:
            raise
        except Exception as exc:
            raise RetrievalError("KNOWLEDGE_SEARCH_UNAVAILABLE", stage="knowledge_search") from exc
        accepted = tuple(item for item in evidence if item.score >= self._min_score)
        blocks: list[str] = []
        citations: list[str] = []
        used = 0
        for index, item in enumerate(accepted, start=1):
            citation = f"[{index}] {item.title}"
            if item.source_url:
                citation += f" — {item.source_url}"
            dates = []
            if item.effective_from:
                dates.append(f"từ {item.effective_from.isoformat()}")
            if item.effective_to:
                dates.append(f"đến {item.effective_to.isoformat()}")
            if dates:
                citation += f" ({' '.join(dates)})"
            block = f"{citation}\n{item.body.strip()}"
            remaining = self._max_context_characters - used
            if remaining <= 0:
                break
            if len(block) > remaining:
                block = block[:remaining]
            blocks.append(block)
            citations.append(citation)
            used += len(block)
        return GroundedContext(tuple(accepted[:len(blocks)]), "\n\n".join(blocks), tuple(citations))
