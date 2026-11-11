import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from intent_stubs import StubIntentClassifier

from app.application.use_cases.stream_chat import StreamChatUseCase
from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.chat_request import ChatClaim, ChatCommit, ChatRequest, ChatSnapshot
from app.domain.entities.knowledge_evidence import GroundedContext, KnowledgeEvidence
from app.domain.errors import RetrievalError
from app.domain.ports.chat_completion import ChatCompletionPort
from app.domain.ports.chat_turn_repository import ChatTurnRepository
from app.infrastructure.prompts.loader import get_prompt_catalog


class FakeRepository(ChatTurnRepository):
    def __init__(self, *, history=()):
        self.committed_answer = None
        self.committed_estimate = None
        self.state_update = None
        self.history = history

    async def claim(self, request, request_hash):
        return ChatClaim("claimed", ChatSnapshot(
            0, self.history, uuid4(), uuid4(),
        ))

    async def commit(self, request, *, request_id, lease_token, snapshot_version, answer, state_update=None, estimate=None):
        self.committed_answer = answer
        self.committed_estimate = estimate
        self.state_update = state_update
        return ChatCommit({"reply": answer, "estimate": estimate}, 200, uuid4(), uuid4(), snapshot_version + 1)

    async def fail(self, request, *, request_id, lease_token, error_code, response_status, retryable):
        return True


class FakeCompletion(ChatCompletionPort):
    def __init__(self, answer="The rate is 70–85%."):
        self.answer = answer
        self.calls = 0
        self.knowledge_context = ""
        self.history = ()

    async def stream_reply(self, text, *, history=(), guidance="", knowledge_context="") -> AsyncIterator[str]:
        self.calls += 1
        self.knowledge_context = knowledge_context
        self.history = history
        yield self.answer


class FakeRetrieval:
    def __init__(self, context=None, error=None):
        self.context = context or GroundedContext((), "", ())
        self.error = error
        self.queries = []

    async def retrieve(self, text):
        self.queries.append(text)
        if self.error is not None:
            raise self.error
        return self.context


@pytest.fixture
def grounded_context():
    item = KnowledgeEvidence(
        chunk_id=uuid4(), document_id=uuid4(), title="Lãi suất chính thức",
        source_url="https://bank.example/rates", body="Tài liệu nêu mức 8%.", score=0.9,
    )
    return GroundedContext(
        (item,), "[1] Lãi suất chính thức\nTài liệu nêu mức 8%.",
        ("[1] Lãi suất chính thức — https://bank.example/rates",),
    )


def execute(completion, retrieval, text, repository=None, *, intent=ChatIntent.RETRIEVAL):
    repository = repository or FakeRepository()
    request = ChatRequest(uuid4(), uuid4(), text, None)
    events = asyncio.run(collect(StreamChatUseCase(
        completion, repository, prompts=get_prompt_catalog(), retrieval=retrieval,
        classifier=StubIntentClassifier(intent),
    ).execute(request)))
    return events, repository


async def collect(events):
    return [event async for event in events]


@pytest.mark.parametrize("text, expected", [
    ("Xin chào", "Xin chào!"), ("Cảm ơn bạn", "Không có gì!"), ("Tạm biệt", "Tạm biệt!"),
])
def test_general_skips_retrieval_and_model(text, expected):
    completion = FakeCompletion()
    retrieval = FakeRetrieval(error=AssertionError("must not retrieve"))
    events, repository = execute(completion, retrieval, text, intent=ChatIntent.GENERAL)
    assert expected in repository.committed_answer
    assert retrieval.queries == []
    assert completion.calls == 0
    assert [event.event for event in events] == ["delta", "done"]
    assert repository.state_update.intent == "general"
    assert repository.committed_estimate is None
    assert events[-1].data["estimate"] is None


@pytest.mark.parametrize("text", [
    "Lãi suất vay mua nhà bao nhiêu?", "Tôi muốn vay 10 tỷ", "Còn ngân hàng đó thì sao?",
])
def test_missing_evidence_never_calls_model_or_starts_slot_collection(text):
    completion = FakeCompletion()
    retrieval = FakeRetrieval()
    events, repository = execute(completion, retrieval, text)
    assert "chưa tìm thấy tài liệu đã được duyệt" in repository.committed_answer
    assert "70–85%" not in repository.committed_answer
    assert "thời hạn vay" not in repository.committed_answer
    assert completion.calls == 0
    assert retrieval.queries == [text]
    assert [event.event for event in events] == ["delta", "done"]
    assert repository.state_update.intent == "retrieval"
    assert repository.committed_estimate is None
    assert events[-1].data["estimate"] is None


@pytest.mark.parametrize("retrieval, code", [
    (None, "RETRIEVAL_NOT_CONFIGURED"),
    (FakeRetrieval(error=RuntimeError("private details")), "RETRIEVAL_UNAVAILABLE"),
    (FakeRetrieval(error=TimeoutError()), "RETRIEVAL_TIMEOUT"),
])
def test_unavailable_retrieval_fails_closed(retrieval, code):
    completion = FakeCompletion()
    repository = FakeRepository()
    with pytest.raises(RetrievalError) as caught:
        execute(completion, retrieval, "Hồ sơ cần gì?", repository)
    assert caught.value.code == code
    assert completion.calls == 0
    assert repository.committed_answer is None
    assert "private details" not in str(caught.value)


def test_grounded_response_places_model_disclaimer_before_system_source_footer(grounded_context):
    model_answer = (
        "Tài liệu đã duyệt nêu mức 8%. [1]\n\n"
        "Lưu ý: Thông tin chỉ mang tính tham khảo; bạn nên xác nhận điều kiện áp dụng trực tiếp với ngân hàng."
    )
    completion = FakeCompletion(model_answer)
    retrieval = FakeRetrieval(grounded_context)
    events, repository = execute(completion, retrieval, "Chào bạn, lãi suất bao nhiêu?")

    assert completion.calls == 1
    assert len(retrieval.queries) == 1
    assert "Tài liệu nêu mức 8%." in completion.knowledge_context
    assert repository.committed_answer == (
        model_answer + "\n\nNguồn tham khảo: [1] Lãi suất chính thức — https://bank.example/rates"
    )
    assert any(event.event == "delta" and "Nguồn tham khảo" in event.data.get("text", "") for event in events)
    assert "".join(event.data["text"] for event in events if event.event == "delta") == repository.committed_answer


def test_retrieval_guidance_requires_model_generated_disclaimer_before_footer():
    from app.domain.ports.prompt_catalog import PromptName

    guidance = get_prompt_catalog().get(PromptName.RETRIEVAL_GUIDANCE)
    assert "một câu disclaimer ngắn" in guidance
    assert "Lưu ý:" in guidance
    assert "trước phần nguồn tham khảo do ứng dụng nối thêm" in guidance
    assert "không tự tạo danh mục nguồn" in guidance


def test_general_reply_does_not_receive_retrieval_disclaimer_or_source_footer():
    completion = FakeCompletion("A friendly answer")
    events, repository = execute(
        completion, FakeRetrieval(), "Xin chào", intent=ChatIntent.GENERAL,
    )

    assert repository.committed_answer.startswith("Xin chào!")
    assert "Lưu ý:" not in repository.committed_answer
    assert "Nguồn tham khảo:" not in repository.committed_answer
    assert completion.calls == 0
    assert [event.event for event in events] == ["delta", "done"]


def test_no_evidence_reply_does_not_receive_model_disclaimer_or_footer():
    completion = FakeCompletion()
    events, repository = execute(completion, FakeRetrieval(), "Hồ sơ vay cần gì?")

    assert "chưa tìm thấy tài liệu đã được duyệt" in repository.committed_answer
    assert "Lưu ý:" not in repository.committed_answer
    assert "Nguồn tham khảo:" not in repository.committed_answer
    assert completion.calls == 0
    assert [event.event for event in events] == ["delta", "done"]


def test_deterministic_estimate_reply_does_not_receive_retrieval_disclaimer_or_footer(grounded_context):
    class EstimateStub:
        async def execute(self, text, session):
            from types import SimpleNamespace
            return SimpleNamespace(handled=True, answer="Ước tính trả góp: 10 triệu đồng.", session=session, result=None)

    repository = FakeRepository()
    request = ChatRequest(uuid4(), uuid4(), "Tính khoản vay", None)
    events = asyncio.run(collect(StreamChatUseCase(
        FakeCompletion(), repository, prompts=get_prompt_catalog(),
        retrieval=FakeRetrieval(grounded_context), classifier=StubIntentClassifier(ChatIntent.ESTIMATE),
        estimate=EstimateStub(),
    ).execute(request)))

    assert repository.committed_answer == "Ước tính trả góp: 10 triệu đồng."
    assert "Lưu ý:" not in repository.committed_answer
    assert "Nguồn tham khảo:" not in repository.committed_answer
    assert [event.event for event in events] == ["delta", "done"]
    assert events[-1].data["reply"] == repository.committed_answer


def test_disclaimerless_model_answer_is_not_rewritten_by_the_application(grounded_context):
    model_answer = "Tài liệu đã duyệt nêu mức 8%. [1]"
    _, repository = execute(FakeCompletion(model_answer), FakeRetrieval(grounded_context), "Lãi suất?")

    # The app owns citation metadata/footer only; disclaimer generation is best-effort prompt behavior.
    assert repository.committed_answer.startswith(model_answer)
    assert "Nguồn tham khảo:" in repository.committed_answer
    assert "Lưu ý:" not in repository.committed_answer


def test_grounded_response_omits_uncited_sources_from_footer(grounded_context):
    second = KnowledgeEvidence(
        chunk_id=uuid4(), document_id=uuid4(), title="Điều kiện vay",
        source_url="https://bank.example/eligibility", body="Có điều kiện thu nhập.", score=0.8,
    )
    context = GroundedContext(
        (*grounded_context.evidence, second), grounded_context.prompt_context,
        (*grounded_context.citations, "[2] Điều kiện vay — https://bank.example/eligibility"),
    )
    completion = FakeCompletion("Mức lãi suất là 8%. [1]")
    _, repository = execute(completion, FakeRetrieval(context), "Lãi suất bao nhiêu?")
    assert "Nguồn tham khảo: [1] Lãi suất chính thức — https://bank.example/rates" in repository.committed_answer
    assert "Điều kiện vay" not in repository.committed_answer


def test_grounded_response_omits_footer_for_unknown_only_citation(grounded_context):
    completion = FakeCompletion("Mức lãi suất là 8%. [9]")
    _, repository = execute(completion, FakeRetrieval(grounded_context), "Lãi suất bao nhiêu?")
    assert "Nguồn tham khảo:" not in repository.committed_answer
    assert "[9]" in repository.committed_answer


def test_grounded_response_keeps_multiple_valid_citations_once(grounded_context):
    second = KnowledgeEvidence(
        chunk_id=uuid4(), document_id=uuid4(), title="Điều kiện vay",
        source_url=None, body="Có điều kiện thu nhập.", score=0.8,
    )
    context = GroundedContext(
        (*grounded_context.evidence, second), grounded_context.prompt_context,
        (*grounded_context.citations, "[2] Điều kiện vay"),
    )
    completion = FakeCompletion("Điều kiện được nêu. [2] Lãi suất là 8%. [1] [2]")
    _, repository = execute(completion, FakeRetrieval(context), "Thông tin vay?")
    assert repository.committed_answer.endswith(
        "Nguồn tham khảo: [1] Lãi suất chính thức — https://bank.example/rates; [2] Điều kiện vay"
    )


def test_followups_use_history_without_workflow_state(grounded_context):
    history = (("user", "Lãi suất vay mua nhà ngân hàng A?"), ("assistant", "Câu trả lời cũ"))
    repository = FakeRepository(history=history)
    completion = FakeCompletion("Theo tài liệu...")
    retrieval = FakeRetrieval(grounded_context)
    execute(completion, retrieval, "Còn ngân hàng đó thì sao?", repository)
    assert "Lãi suất vay mua nhà ngân hàng A?" in retrieval.queries[0]
    assert "Câu trả lời cũ" not in retrieval.queries[0]
    assert completion.history == history
    assert repository.state_update.intent == "retrieval"


def test_blank_prompt_context_is_not_usable_evidence(grounded_context):
    completion = FakeCompletion()
    execute(completion, FakeRetrieval(GroundedContext(grounded_context.evidence, " ", ())), "Hồ sơ vay?")
    assert completion.calls == 0
