import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from app.application.use_cases.stream_chat import StreamChatUseCase
from app.domain.entities.chat_request import ChatClaim, ChatCommit, ChatRequest, ChatSnapshot
from app.domain.entities.knowledge_evidence import GroundedContext, KnowledgeEvidence
from app.domain.errors import RetrievalError
from app.domain.ports.chat_completion import ChatCompletionPort
from app.domain.ports.chat_turn_repository import ChatTurnRepository
from app.infrastructure.prompts.loader import get_prompt_catalog


class FakeRepository(ChatTurnRepository):
    def __init__(self, *, history=()):
        self.committed_answer = None
        self.state_update = None
        self.history = history

    async def claim(self, request, request_hash):
        return ChatClaim("claimed", ChatSnapshot(
            0, self.history, uuid4(), uuid4(),
        ))

    async def commit(self, request, *, request_id, lease_token, snapshot_version, answer, state_update=None):
        self.committed_answer = answer
        self.state_update = state_update
        return ChatCommit({"reply": answer}, 200, uuid4(), uuid4(), snapshot_version + 1)

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


def execute(completion, retrieval, text, repository=None):
    repository = repository or FakeRepository()
    request = ChatRequest(uuid4(), uuid4(), text, None)
    events = asyncio.run(collect(StreamChatUseCase(
        completion, repository, prompts=get_prompt_catalog(), retrieval=retrieval,
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
    events, repository = execute(completion, retrieval, text)
    assert expected in repository.committed_answer
    assert retrieval.queries == []
    assert completion.calls == 0
    assert [event.event for event in events] == ["delta", "done"]
    assert repository.state_update.intent == "general"


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


def test_grounded_response_receives_sources_and_appends_citation(grounded_context):
    completion = FakeCompletion("Tài liệu đã duyệt nêu mức 8%.")
    retrieval = FakeRetrieval(grounded_context)
    events, repository = execute(completion, retrieval, "Chào bạn, lãi suất bao nhiêu?")
    assert completion.calls == 1
    assert len(retrieval.queries) == 1
    assert "Tài liệu nêu mức 8%." in completion.knowledge_context
    assert "Nguồn tham khảo: [1] Lãi suất chính thức — https://bank.example/rates" in repository.committed_answer
    assert any(event.event == "delta" and "Nguồn tham khảo" in event.data.get("text", "") for event in events)
    assert "".join(event.data["text"] for event in events if event.event == "delta") == repository.committed_answer


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
