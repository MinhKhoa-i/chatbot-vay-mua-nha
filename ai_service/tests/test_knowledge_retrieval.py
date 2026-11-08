import asyncio
from dataclasses import replace
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


def test_retrieval_reuses_one_citation_for_all_chunks_from_same_document():
    first = KnowledgeEvidence(
        chunk_id=uuid4(), document_id=uuid4(), title="Quy trình cấp tín dụng",
        source_url="https://bank.example/process", body="Thẩm định hồ sơ.", score=0.9,
    )
    second = replace(first, chunk_id=uuid4(), body="Quyết định cấp tín dụng.")
    third = replace(first, chunk_id=uuid4(), body="Giám sát sử dụng vốn.")
    service = KnowledgeRetrievalService(FakeRepository((first, second, third)), FakeEmbedder())

    context = asyncio.run(service.retrieve("lãi suất vay mua nhà"))

    assert context.evidence == (first, second, third)
    assert context.citations == ("[1] Quy trình cấp tín dụng — https://bank.example/process",)
    assert context.prompt_context.count("[1] Quy trình cấp tín dụng") == 3
    assert "[2]" not in context.prompt_context
    for item in context.evidence:
        assert item.body in context.prompt_context


def test_retrieval_numbers_distinct_documents_in_order_even_with_identical_titles():
    first = KnowledgeEvidence(
        chunk_id=uuid4(), document_id=uuid4(), title="Tên tài liệu",
        source_url=None, body="Đoạn của tài liệu thứ nhất.", score=0.9,
    )
    second = replace(first, chunk_id=uuid4(), document_id=uuid4(), body="Đoạn của tài liệu thứ hai.")
    first_again = replace(first, chunk_id=uuid4(), body="Đoạn tiếp theo của tài liệu thứ nhất.")
    third = replace(first, chunk_id=uuid4(), document_id=uuid4(), body="Đoạn của tài liệu thứ ba.")
    service = KnowledgeRetrievalService(
        FakeRepository((first, second, first_again, third)), FakeEmbedder(),
    )

    context = asyncio.run(service.retrieve("lãi suất vay mua nhà"))

    assert context.evidence == (first, second, first_again, third)
    assert context.citations == ("[1] Tên tài liệu", "[2] Tên tài liệu", "[3] Tên tài liệu")
    assert context.prompt_context.split("\n\n") == [
        f"[1] Tên tài liệu\n{first.body}",
        f"[2] Tên tài liệu\n{second.body}",
        f"[1] Tên tài liệu\n{first_again.body}",
        f"[3] Tên tài liệu\n{third.body}",
    ]


def test_retrieval_does_not_cite_documents_excluded_by_context_limit():
    first = KnowledgeEvidence(
        chunk_id=uuid4(), document_id=uuid4(), title="Hồ sơ",
        source_url=None, body="Chuẩn bị hồ sơ.", score=0.9,
    )
    second = replace(first, chunk_id=uuid4(), body="Nộp hồ sơ.")
    excluded = replace(first, chunk_id=uuid4(), document_id=uuid4(), title="Nguồn bị loại")
    expected_context = f"[1] Hồ sơ\n{first.body}\n\n[1] Hồ sơ\n{second.body}"
    service = KnowledgeRetrievalService(
        FakeRepository((first, second, excluded)), FakeEmbedder(),
        max_context_characters=len(expected_context) - 2,
    )

    context = asyncio.run(service.retrieve("lãi suất vay mua nhà"))

    assert context.evidence == (first, second)
    assert context.prompt_context == expected_context
    assert context.citations == ("[1] Hồ sơ",)
    assert excluded.title not in context.prompt_context


def test_retrieval_keeps_citation_for_a_partially_included_document():
    first = KnowledgeEvidence(
        chunk_id=uuid4(), document_id=uuid4(), title="Hồ sơ",
        source_url=None, body="Chuẩn bị hồ sơ.", score=0.9,
    )
    second = replace(first, chunk_id=uuid4(), document_id=uuid4(), title="Quy trình", body="Nộp hồ sơ để thẩm định.")
    first_block = f"[1] Hồ sơ\n{first.body}"
    second_header = "[2] Quy trình\n"
    service = KnowledgeRetrievalService(
        FakeRepository((first, second)), FakeEmbedder(),
        max_context_characters=len(first_block) + len(second_header) + 3,
    )

    context = asyncio.run(service.retrieve("lãi suất vay mua nhà"))

    assert context.evidence == (first, second)
    assert context.citations == ("[1] Hồ sơ", "[2] Quy trình")
    assert context.prompt_context == f"{first_block}\n\n{second_header}{second.body[:3]}"
