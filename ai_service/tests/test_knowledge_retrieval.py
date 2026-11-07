import asyncio
from datetime import date
from uuid import uuid4

from app.application.services.knowledge_retrieval import KnowledgeRetrievalService
from app.domain.entities.knowledge_evidence import KnowledgeEvidence


class FakeEmbedder:
    async def embed_documents(self, texts):
        assert texts == ["lãi suất vay mua nhà"]
        return [[0.0, 1.0]]


class FakeRepository:
    def __init__(self, evidence):
        self.evidence = evidence
        self.query = None

    async def search_approved(self, query):
        self.query = query
        return self.evidence


def test_retrieval_builds_bounded_cited_context_from_repository_evidence():
    source = KnowledgeEvidence(
        chunk_id=uuid4(), document_id=uuid4(), title="Biểu lãi suất đã duyệt",
        source_url="https://bank.example/rates", body="Lãi suất tham khảo là 8%/năm.", score=0.82,
        bank_code="EXAMPLE", product_type="mortgage", effective_from=date(2026, 1, 1),
    )
    repository = FakeRepository((source,))
    service = KnowledgeRetrievalService(repository, FakeEmbedder(), limit=3)

    context = asyncio.run(service.retrieve("lãi suất vay mua nhà"))

    assert repository.query.limit == 3
    assert repository.query.embedding == (0.0, 1.0)
    assert "[1] Biểu lãi suất đã duyệt" in context.prompt_context
    assert "https://bank.example/rates" in context.prompt_context
    assert "Lãi suất tham khảo là 8%/năm." in context.prompt_context
    assert context.citations == ("[1] Biểu lãi suất đã duyệt — https://bank.example/rates (từ 2026-01-01)",)


def test_retrieval_rejects_low_score_evidence_and_limits_prompt_context():
    weak = KnowledgeEvidence(
        chunk_id=uuid4(), document_id=uuid4(), title="Weak", source_url=None,
        body="untrusted due to low score", score=0.01,
    )
    repository = FakeRepository((weak,))
    service = KnowledgeRetrievalService(repository, FakeEmbedder(), min_score=0.2)

    context = asyncio.run(service.retrieve("lãi suất vay mua nhà"))

    assert context.evidence == ()
    assert context.prompt_context == ""
    assert context.citations == ()
