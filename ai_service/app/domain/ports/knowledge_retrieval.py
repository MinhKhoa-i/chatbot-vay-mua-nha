from typing import Protocol

from app.domain.entities.knowledge_evidence import GroundedContext


class KnowledgeRetriever(Protocol):
    """Read-only knowledge search, independent of storage and embedding providers."""

    async def retrieve(self, text: str) -> GroundedContext: ...
