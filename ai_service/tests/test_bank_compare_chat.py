from uuid import uuid4

import pytest

from intent_stubs import StubIntentClassifier

from app.application.use_cases.compare_banks import CompareBanksUseCase
from app.domain.entities.bank_compare_session import BankCompareExtraction, BankCompareSession
from app.domain.entities.bank_rank import BankRankResult
from app.domain.entities.chat_orchestration import ChatIntent
from app.application.use_cases.stream_chat import StreamChatUseCase
from app.domain.entities.chat_request import ChatClaim, ChatRequest, ChatSnapshot
from app.infrastructure.prompts.loader import get_prompt_catalog
from test_chat_grounding import FakeCompletion, FakeRepository, FakeRetrieval


class Extractor:
    def __init__(self, *extractions):
        self.extractions = iter(extractions)

    async def extract(self, text, session):
        return next(self.extractions)


class Ranker:
    def __init__(self):
        self.calls = []

    async def rank(self, request):
        self.calls.append(request)
        return BankRankResult((), (), {}, "2026-11-16", False)


class Repository(FakeRepository):
    def __init__(self, session=BankCompareSession()):
        super().__init__()
        self.bank_compare_session = session

    async def claim(self, request, request_hash):
        return ChatClaim("claimed", ChatSnapshot(
            0, (), uuid4(), uuid4(), bank_compare_session=self.bank_compare_session,
        ))

    async def commit(self, *args, **kwargs):
        result = await super().commit(*args, **kwargs)
        if self.state_update.bank_compare_session is not None:
            self.bank_compare_session = self.state_update.bank_compare_session
        return result


@pytest.mark.asyncio
async def test_bank_compare_session_continues_until_required_fields_then_ranks():
    repository = Repository()
    classifier = StubIntentClassifier(ChatIntent.BANK_COMPARE)
    ranker = Ranker()
    compare = CompareBanksUseCase(Extractor(
        BankCompareExtraction("update", {"amount": 1_000_000_000}),
        BankCompareExtraction("update", {"years": 20, "assumed_floating_rate": 9}),
    ), ranker, get_prompt_catalog())
    retrieval = FakeRetrieval(error=AssertionError("must not retrieve"))
    completion = FakeCompletion()
    case = StreamChatUseCase(
        completion, repository, prompts=get_prompt_catalog(), classifier=classifier,
        retrieval=retrieval, bank_compare=compare,
    )

    first = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "Vay 1 tỷ", None))]
    second = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "20 năm, giả định 9%", 1))]

    assert first[-1].event == second[-1].event == "done"
    assert "thời hạn vay" in first[0].data["text"]
    assert repository.bank_compare_session.status == "completed"
    assert len(ranker.calls) == 1
    assert ranker.calls[0].amount == 1_000_000_000
    assert ranker.calls[0].assumed_floating_rate == 9
    assert len(classifier.calls) == 1
    assert completion.calls == 0 and retrieval.queries == []
    assert repository.state_update.bank_compare_session == repository.bank_compare_session


@pytest.mark.asyncio
async def test_unrelated_message_during_bank_compare_falls_back_without_clearing_session():
    state = BankCompareSession(amount=1_000_000_000, status="collecting")
    repository = Repository(state)
    classifier = StubIntentClassifier(ChatIntent.RETRIEVAL)
    compare = CompareBanksUseCase(
        Extractor(BankCompareExtraction("unrelated", {})), Ranker(), get_prompt_catalog(),
    )
    retrieval = FakeRetrieval()
    case = StreamChatUseCase(
        FakeCompletion(), repository, prompts=get_prompt_catalog(), classifier=classifier,
        retrieval=retrieval, bank_compare=compare,
    )
    question = "Hồ sơ vay cần những gì?"
    events = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), question, None))]

    assert events[-1].event == "done"
    assert retrieval.queries == [question]
    assert repository.bank_compare_session == state
    assert repository.state_update.bank_compare_session is None
    assert classifier.calls == [(question, ())]
