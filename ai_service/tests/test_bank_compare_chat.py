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
        self.last_assistant_messages = []

    async def extract(self, text, session, *, last_assistant_message=None):
        self.last_assistant_messages.append(last_assistant_message)
        return next(self.extractions)


class Ranker:
    def __init__(self):
        self.calls = []

    async def rank(self, request):
        self.calls.append(request)
        return BankRankResult((), (), {}, "2026-11-16", False)


class Repository(FakeRepository):
    def __init__(self, session=BankCompareSession(), memory=None, history=()):
        super().__init__()
        self.bank_compare_session = session
        self.history = tuple(history)
        if memory is not None:
            self.conversation_memory = memory

    async def claim(self, request, request_hash):
        return ChatClaim("claimed", ChatSnapshot(
            0, self.history, uuid4(), uuid4(), bank_compare_session=self.bank_compare_session,
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
    completion = FakeCompletion("Hiện chưa có gói vay phù hợp để xếp hạng.")
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
async def test_two_turn_comparison_preserves_llm_reply_with_five_percent_assumption():
    import json
    from dataclasses import replace

    from test_bank_compare import Ranker as ResultRanker, ranked_bank

    repository = Repository()
    classifier = StubIntentClassifier(ChatIntent.BANK_COMPARE)
    result = BankRankResult(
        (replace(ranked_bank(), floating_rate=Decimal("5")),), (),
        {"floating_rate": Decimal("5")}, "2026-11-16", True,
    )
    ranker = ResultRanker(result)
    completion = FakeCompletion(
        "Với khoản vay 1,5 tỷ trong 20 năm, lãi sau ưu đãi giả định là 5.0%/năm. "
        "Khoản trả tháng đầu là 14,475,325 VND. Các số liệu chỉ mang tính minh họa."
    )
    compare = CompareBanksUseCase(Extractor(
        BankCompareExtraction("update", {"amount": 1_500_000_000, "years": 20}),
        BankCompareExtraction("update", {"assumed_floating_rate": Decimal("5")}),
    ), ranker, get_prompt_catalog())
    case = StreamChatUseCase(
        completion, repository, prompts=get_prompt_catalog(), classifier=classifier,
        bank_compare=compare,
    )
    conversation_id = uuid4()

    first = [event async for event in case.execute(ChatRequest(
        conversation_id, uuid4(),
        "Mình cần vay 1,5 tỷ trong 20 năm, ngân hàng nào có lợi nhất?", None,
    ))]
    assert first[-1].event == "done"
    assert "lãi sau ưu đãi" in first[0].data["text"]
    assert completion.calls == 0 and ranker.calls == []

    second = [event async for event in case.execute(ChatRequest(
        conversation_id, uuid4(), "giả sử lãi là 5%", 1,
    ))]

    assert len(ranker.calls) == completion.calls == len(classifier.calls) == 1
    assert ranker.calls[0].amount == 1_500_000_000
    assert ranker.calls[0].years == 20
    assert ranker.calls[0].assumed_floating_rate == Decimal("5")
    assert [event.event for event in second] == ["delta", "done"]
    assert second[0].data["text"] == second[-1].data["reply"] == completion.answer
    assert repository.committed_answer == completion.answer
    assert repository.bank_compare_session.status == "completed"
    assert repository.conversation_memory.assumed_floating_rate == Decimal("5")
    assert json.loads(completion.knowledge_context)["scenario"]["assumed_floating_rate"] == "5"


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
@pytest.mark.parametrize("draft,valid", [
    ("Vay 1.500.000.000 VND trong 20 năm, lãi giả định 10%. "
     "Khoản trả đầu 14.475.325 VND. Cập nhật 16/11/2026.", True),
    ("Lãi cơ sở 7,5%/năm; giá nhà 2.000.000.000 VND; trả trước 60 tháng, ân hạn 6 tháng.", True),
    ("Tổng chi phí 466.928.374 VND, tiền lãi 438.579.027 VND, phí 28.349.347 VND.", True),
    ("Hiện có phương án để bạn tham khảo.", True),
    ("Khoản trả đầu 1.955.009.765 VND.", False),
    ("Lãi suất 10,5%/năm.", False),
    ("Lãi suất -10%/năm.", False),
    ("Lãi suất 2​0%/năm.", True),
    ("Lãi suất 1​0​0%/năm.", False),
    ("Lãi suất −10%/năm.", False),
    ("1. Agribank; cập nhật 2026-11-16.", True),
    ("Lãi cơ sở 7.5%/năm.", True),
    ("Khoản vay 1500000000 VND.", True),
    ("Khoản vay 1,5 tỷ trong 20 năm, lãi giả định 10.0%/năm.", True),
    ("Khoản vay 1.5 tỷ; khoản trả đầu 14,475,325 VND.", True),
    ("Khoản vay 1,6 tỷ VND.", False),
    ("Khoản trả đầu 14,475,326 VND.", False),
    ("Lãi suất 10.5%/năm.", False),
])
async def test_comparison_validates_buffered_draft_before_emitting(draft, valid, caplog):
    from dataclasses import replace

    from test_bank_compare import Ranker as ResultRanker, ranked_bank

    session = BankCompareSession(
        amount=1_500_000_000, years=20, assumed_floating_rate=Decimal("10"),
        base_rate=Decimal("7.5"), property_value=2_000_000_000,
        prepay_month=60, grace_period_months=6, status="collecting",
    )
    result = BankRankResult(
        (ranked_bank(),), (), {"floating_rate": Decimal("10")}, "2026-11-16", True,
    )
    repository = Repository(session)
    compare = CompareBanksUseCase(Extractor(BankCompareExtraction("update", {})),
                                  ResultRanker(result), get_prompt_catalog())
    fallback = compare._render_result(session, result)
    completed = False

    class FragmentedCompletion:
        async def stream_reply(self, text, **kwargs):
            nonlocal completed
            midpoint = len(draft) // 2
            yield draft[:midpoint]
            yield draft[midpoint:]
            completed = True

    case = StreamChatUseCase(
        FragmentedCompletion(), repository, prompts=get_prompt_catalog(),
        classifier=StubIntentClassifier(ChatIntent.BANK_COMPARE), bank_compare=compare,
    )
    events = []
    async for event in case.execute(ChatRequest(uuid4(), uuid4(), "So sánh", None)):
        assert completed, "Do not emit unvalidated completion fragments"
        events.append(event)

    expected = draft if valid else fallback
    assert [event.event for event in events] == ["delta", "done"]
    assert events[0].data["text"] == expected
    assert events[-1].data["reply"] == repository.committed_answer == expected
    assert repository.bank_compare_session == replace(session, status="completed")
    assert ("BANK_COMPARE_NUMBER_MISMATCH" in caplog.text) is not valid
    assert draft not in caplog.text


@pytest.mark.asyncio
async def test_general_chat_keeps_incremental_streaming():
    repository = Repository()

    class FragmentedCompletion:
        async def stream_reply(self, text, **kwargs):
            yield "Xin chào "
            assert repository.committed_answer is None
            yield "123456789"

    case = StreamChatUseCase(
        FragmentedCompletion(), repository, prompts=get_prompt_catalog(),
        classifier=StubIntentClassifier(ChatIntent.GENERAL),
    )
    events = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "Chào", None))]

    assert [event.data["text"] for event in events if event.event == "delta"] == [
        "Xin chào ", "123456789",
    ]
    assert repository.committed_answer == "Xin chào 123456789"


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
    assert events == []
    assert repository.failure["error_code"] == "MODEL_UNAVAILABLE"
    assert repository.committed_answer is None and repository.state_update is None
    assert repository.bank_compare_session == state
    assert len(ranker.calls) == 1


@pytest.mark.asyncio
async def test_active_bank_compare_passes_last_assistant_question_to_extractor():
    assistant_question = (
        "Các ngân hàng chưa công bố lãi sau ưu đãi. Bạn muốn giả định lãi sau ưu đãi "
        "bao nhiêu %/năm để so sánh (ví dụ 10)?"
    )
    state = BankCompareSession(amount=1_500_000_000, years=20, status="collecting")
    repository = Repository(
        state,
        history=(
            ("user", "Với khoản vay 1,5 tỷ đồng trong 20 năm, ngân hàng nào là tốt nhất?"),
            ("assistant", assistant_question),
        ),
    )
    extractor = Extractor(BankCompareExtraction("update", {"assumed_floating_rate": Decimal("5")}))
    ranker = Ranker()
    case = StreamChatUseCase(
        FakeCompletion("Hiện chưa có gói vay phù hợp để xếp hạng."),
        repository,
        prompts=get_prompt_catalog(),
        classifier=StubIntentClassifier(ChatIntent.RETRIEVAL),
        retrieval=FakeRetrieval(error=AssertionError("must not retrieve")),
        bank_compare=CompareBanksUseCase(extractor, ranker, get_prompt_catalog()),
    )

    events = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "5%", 1))]

    assert events[-1].event == "done"
    assert extractor.last_assistant_messages == [assistant_question]
    assert len(ranker.calls) == 1
    assert ranker.calls[0].assumed_floating_rate == Decimal("5")


@pytest.mark.asyncio
async def test_active_bank_compare_unrelated_still_falls_back_to_classification_and_retrieval():
    state = BankCompareSession(amount=1_500_000_000, years=20, status="collecting")
    repository = Repository(state)
    ranker = Ranker()
    retrieval = FakeRetrieval()
    case = StreamChatUseCase(
        FakeCompletion(),
        repository,
        prompts=get_prompt_catalog(),
        classifier=StubIntentClassifier(ChatIntent.BANK_COMPARE),
        retrieval=retrieval,
        bank_compare=CompareBanksUseCase(
            Extractor(BankCompareExtraction("unrelated", {})), ranker, get_prompt_catalog(),
        ),
    )

    events = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "không rõ", 1))]

    assert events[-1].event == "done"
    assert retrieval.queries == ["không rõ"]
    assert ranker.calls == []
    assert repository.bank_compare_session == state
    assert repository.state_update.bank_compare_session is None


@pytest.mark.asyncio
async def test_idle_bank_compare_unrelated_still_falls_back_to_retrieval():
    repository = Repository()
    ranker = Ranker()
    retrieval = FakeRetrieval()
    question = "BIDV quảng cáo lãi suất 5%, có đúng không?"
    case = StreamChatUseCase(
        FakeCompletion(),
        repository,
        prompts=get_prompt_catalog(),
        classifier=StubIntentClassifier(ChatIntent.BANK_COMPARE),
        retrieval=retrieval,
        bank_compare=CompareBanksUseCase(
            Extractor(BankCompareExtraction("unrelated", {})), ranker, get_prompt_catalog(),
        ),
    )

    events = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), question, None))]

    assert events[-1].event == "done"
    assert retrieval.queries == [question]
    assert ranker.calls == []
    assert repository.bank_compare_session == BankCompareSession()
