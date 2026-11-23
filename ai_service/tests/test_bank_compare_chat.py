from decimal import Decimal
from uuid import uuid4

import pytest

from intent_stubs import StubIntentClassifier

from app.application.use_cases.compare_banks import CompareBanksUseCase
from app.domain.entities.bank_compare_session import BankCompareExtraction, BankCompareSession
from app.domain.entities.bank_rank import BankRankResult
from app.domain.entities.chat_orchestration import ChatIntent
from app.application.use_cases.stream_chat import StreamChatUseCase
from app.domain.entities.chat_request import ChatClaim, ChatRequest, ChatSnapshot
from app.domain.entities.conversation_memory import ConversationMemory
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
    def __init__(self, session=BankCompareSession(), memory=None):
        super().__init__()
        self.bank_compare_session = session
        if memory is not None:
            self.conversation_memory = memory

    async def claim(self, request, request_hash):
        return ChatClaim("claimed", ChatSnapshot(
            0, (), uuid4(), uuid4(), bank_compare_session=self.bank_compare_session,
            conversation_memory=self.conversation_memory,
        ))

    async def commit(self, *args, **kwargs):
        result = await super().commit(*args, **kwargs)
        if self.state_update.bank_compare_session is not None:
            self.bank_compare_session = self.state_update.bank_compare_session
        if self.state_update.conversation_memory is not None:
            self.conversation_memory = self.state_update.conversation_memory
        return result


@pytest.mark.asyncio
async def test_bank_compare_session_asks_for_assumed_rate_before_ranking():
    repository = Repository()
    classifier = StubIntentClassifier(ChatIntent.BANK_COMPARE)
    ranker = Ranker()
    compare = CompareBanksUseCase(Extractor(
        BankCompareExtraction("update", {"amount": 1_000_000_000}),
        BankCompareExtraction("update", {"years": 20}),
        BankCompareExtraction("update", {"assumed_floating_rate": Decimal("9")}),
    ), ranker, get_prompt_catalog())
    retrieval = FakeRetrieval(error=AssertionError("must not retrieve"))
    completion = FakeCompletion()
    case = StreamChatUseCase(
        completion, repository, prompts=get_prompt_catalog(), classifier=classifier,
        retrieval=retrieval, bank_compare=compare,
    )

    first = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "Vay 1 tỷ", None))]
    assert completion.calls == 0
    second = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "20 năm", 1))]

    assert first[-1].event == second[-1].event == "done"
    assert "thời hạn vay" in first[0].data["text"]
    assert "Các ngân hàng chưa công bố lãi sau ưu đãi. Bạn muốn giả định lãi sau ưu đãi bao nhiêu %/năm để so sánh (ví dụ 10)?" in second[0].data["text"]
    assert repository.bank_compare_session.status == "collecting"
    assert repository.bank_compare_session.assumed_floating_rate is None
    assert ranker.calls == []
    assert completion.calls == 0 and retrieval.queries == []
    assert repository.state_update.bank_compare_session == repository.bank_compare_session

    third = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "9%/năm", 2))]

    assert third[-1].event == "done"
    assert repository.bank_compare_session.status == "completed"
    assert len(ranker.calls) == 1
    assert ranker.calls[0].amount == 1_000_000_000
    assert ranker.calls[0].years == 20
    assert ranker.calls[0].assumed_floating_rate == 9
    assert ranker.calls[0].method == "annuity"
    assert repository.bank_compare_session.method_explicit is False
    assert repository.conversation_memory.repayment_method is None
    assert repository.conversation_memory.grace_period_months == 0
    assert len(classifier.calls) == 1
    assert completion.calls == 1 and retrieval.queries == []
    assert third[0].data["text"] == completion.answer
    assert third[-1].data["reply"] == completion.answer
    assert repository.committed_answer == completion.answer
    import json

    context = json.loads(completion.knowledge_context)
    assert context["scenario"]["amount"] == 1_000_000_000
    assert context["scenario"]["years"] == 20
    assert context["scenario"]["assumed_floating_rate"] == "9"
    assert context["result"]["ranked"] == []
    assert context["result"]["updated_at"] == "2026-11-16"
    assert "Không tự tính toán" in completion.guidance
    assert repository.state_update.bank_compare_session == repository.bank_compare_session


@pytest.mark.asyncio
async def test_bank_compare_inherits_saved_estimate_facts_and_persists_new_facts():
    from decimal import Decimal

    memory = ConversationMemory(
        amount=1_000_000_000,
        years=20,
        user_provided_rate=Decimal("8.5"),
        repayment_method="annuity",
    )
    repository = Repository(memory=memory)
    classifier = StubIntentClassifier(ChatIntent.BANK_COMPARE)
    ranker = Ranker()
    compare = CompareBanksUseCase(Extractor(
        BankCompareExtraction("update", {
            "property_value": 2_000_000_000, "prepay_month": 60, "grace_period_months": 6,
            "base_rate": Decimal("7.5"), "assumed_floating_rate": Decimal("10"),
            "method": "reducing_balance",
        }),
    ), ranker, get_prompt_catalog())
    case = StreamChatUseCase(
        FakeCompletion(), repository, prompts=get_prompt_catalog(), classifier=classifier,
        retrieval=FakeRetrieval(error=AssertionError("must not retrieve")), bank_compare=compare,
    )

    events = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "So sánh khoản vay đó", None))]

    assert events[-1].event == "done"
    assert len(ranker.calls) == 1
    assert ranker.calls[0].amount == 1_000_000_000
    assert ranker.calls[0].years == 20
    assert ranker.calls[0].prepay_month == 60
    assert ranker.calls[0].property_value == 2_000_000_000
    assert ranker.calls[0].grace_period_months == 6
    assert ranker.calls[0].base_rate == 7.5
    assert ranker.calls[0].assumed_floating_rate == 10
    assert ranker.calls[0].method == "reducing_balance"
    assert repository.bank_compare_session.method_explicit is True
    assert repository.conversation_memory.repayment_method == "reducing_balance"
    assert repository.conversation_memory.amount == 1_000_000_000
    assert repository.conversation_memory.years == 20
    assert repository.conversation_memory.property_value == 2_000_000_000
    assert repository.conversation_memory.prepay_month == 60
    assert repository.conversation_memory.grace_period_months == 6
    assert repository.conversation_memory.base_rate == 7.5
    assert repository.conversation_memory.assumed_floating_rate == 10
    assert repository.conversation_memory.user_provided_rate == Decimal("8.5")
    memory_context = repository.conversation_memory.to_prompt_context()
    assert "2,000,000,000 VND" in memory_context
    assert "tháng 60" in memory_context
    assert "6 tháng" in memory_context
    assert "7,5%/năm" in memory_context
    assert "10%/năm" in memory_context


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


@pytest.mark.asyncio
async def test_ranked_result_and_updated_scenario_are_passed_to_completion():
    import json
    from dataclasses import asdict
    from decimal import Decimal

    from app.domain.entities.bank_rank import ExcludedBank
    from test_bank_compare import ranked_bank

    result = BankRankResult(
        (ranked_bank(total_cost=None, prepay_fee=None), ranked_bank()),
        (ExcludedBank("other", "Other", "Thiếu dữ liệu"),),
        {"floating_rate": Decimal("10")}, "2026-11-16", True,
    )

    class ResultRanker(Ranker):
        async def rank(self, request):
            self.calls.append(request)
            return result

    ranker = ResultRanker()
    repository = Repository()
    completion = FakeCompletion("Câu trả lời do model tạo.")
    compare = CompareBanksUseCase(Extractor(BankCompareExtraction("update", {
        "amount": 1_500_000_000, "years": 20, "property_value": 2_000_000_000,
        "prepay_month": 60, "grace_period_months": 6, "base_rate": Decimal("7.5"),
        "assumed_floating_rate": Decimal("9"), "method": "reducing_balance",
    })), ranker, get_prompt_catalog())
    case = StreamChatUseCase(
        completion, repository, prompts=get_prompt_catalog(),
        classifier=StubIntentClassifier(ChatIntent.BANK_COMPARE), bank_compare=compare,
        retrieval=FakeRetrieval(error=AssertionError("must not retrieve")),
    )

    events = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "So sánh", None))]

    context = json.loads(completion.knowledge_context)
    assert context["result"] == json.loads(json.dumps(asdict(result), default=str))
    assert context["scenario"]["assumed_floating_rate"] == "9"
    assert context["scenario"]["base_rate"] == "7.5"
    assert context["scenario"]["property_value"] == 2_000_000_000
    assert context["scenario"]["prepay_month"] == 60
    assert context["scenario"]["grace_period_months"] == 6
    assert context["scenario"]["method"] == "reducing_balance"
    assert completion.calls == len(ranker.calls) == 1
    assert events[-1].data["reply"] == completion.answer
    assert "prepay_fee_is_upper_bound" in completion.guidance
    assert "không phải chỉ dẫn" in completion.guidance


@pytest.mark.asyncio
async def test_cancel_comparison_does_not_call_completion_or_ranker():
    state = BankCompareSession(amount=1_000_000_000, status="collecting")
    repository = Repository(state)
    ranker = Ranker()
    completion = FakeCompletion()
    case = StreamChatUseCase(
        completion, repository, prompts=get_prompt_catalog(),
        classifier=StubIntentClassifier(ChatIntent.BANK_COMPARE),
        bank_compare=CompareBanksUseCase(
            Extractor(BankCompareExtraction("cancel", {})), ranker, get_prompt_catalog(),
        ),
    )

    events = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "Hủy", None))]

    assert events[-1].event == "done"
    assert repository.bank_compare_session == BankCompareSession()
    assert completion.calls == 0 and ranker.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("partial", [False, True])
async def test_comparison_provider_failure_does_not_commit_completed_state(partial):
    from app.domain.ports.chat_completion import ChatProviderUnavailable

    error = ChatProviderUnavailable(code="MODEL_UNAVAILABLE")

    class FailingCompletion:
        async def stream_reply(self, text, **kwargs):
            if partial:
                yield "Nội dung chưa hoàn tất"
            raise error

    class FailureRepository(Repository):
        failure = None

        async def fail(self, request, **kwargs):
            self.failure = kwargs
            return True

    state = BankCompareSession(amount=1_000_000_000, status="collecting")
    repository = FailureRepository(state)
    ranker = Ranker()
    case = StreamChatUseCase(
        FailingCompletion(), repository, prompts=get_prompt_catalog(),
        classifier=StubIntentClassifier(ChatIntent.BANK_COMPARE),
        bank_compare=CompareBanksUseCase(
            Extractor(BankCompareExtraction("update", {
                "years": 20, "assumed_floating_rate": Decimal("9"),
            })), ranker, get_prompt_catalog(),
        ),
    )
    events = []

    with pytest.raises(ChatProviderUnavailable) as caught:
        async for event in case.execute(ChatRequest(uuid4(), uuid4(), "20 năm", None)):
            events.append(event)

    assert caught.value is error
    assert [event.event for event in events] == (["delta"] if partial else [])
    assert repository.failure["error_code"] == "MODEL_UNAVAILABLE"
    assert repository.committed_answer is None and repository.state_update is None
    assert repository.bank_compare_session == state
    assert len(ranker.calls) == 1
