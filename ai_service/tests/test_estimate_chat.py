import json
from dataclasses import replace
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from intent_stubs import StubIntentClassifier
from openai import AsyncOpenAI

from app.application.use_cases.estimate_loan import EstimateLoanUseCase
from app.application.use_cases.stream_chat import StreamChatUseCase
from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.chat_request import ChatClaim, ChatRequest, ChatSnapshot
from app.domain.entities.estimate_session import EstimateExtraction, EstimateSession
from app.domain.entities.loan_estimate import LoanEstimateInput, LoanEstimateResult
from app.domain.ports.estimate_extractor import EstimateExtractionError
from app.domain.ports.loan_calculator import LoanCalculationError
from app.infrastructure.db.conversation_repository import PostgresConversationRepository
from app.infrastructure.db.estimate_state_codec import decode_estimate_session, encode_estimate_session
from app.infrastructure.llm.openai_estimate_extractor import OpenAIEstimateExtractor
from app.infrastructure.prompts.loader import get_prompt_catalog
from app.infrastructure.security.payload_cipher import PayloadCipherError
from test_chat_grounding import FakeCompletion, FakeRepository, FakeRetrieval
from test_llm_intent_classifier import completion_response


class Extractor:
    def __init__(self, *extractions):
        self.extractions = iter(extractions)
        self.calls = []

    async def extract(self, text, session):
        self.calls.append((text, session))
        return next(self.extractions)


class Calculator:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    async def estimate(self, request):
        self.calls.append(request)
        if self.error:
            raise self.error
        # Deliberately arbitrary values: presentation must use backend values, never recompute.
        return LoanEstimateResult(request, 1234567, 9876543, "2026-10-31")


async def test_collect_confirm_update_and_render_only_backend_numbers():
    extractor = Extractor(
        EstimateExtraction("update", {"amount": 1_000_000_000}),
        EstimateExtraction("update", {"years": 20, "rate": Decimal("9")}),
        EstimateExtraction("update", {"method": "annuity", "promo_duration_months": 0}),
        EstimateExtraction("update", {"years": 25}),
        EstimateExtraction("confirm", {}),
    )
    calculator = Calculator()
    case = EstimateLoanUseCase(extractor, calculator, get_prompt_catalog())
    first = await case.execute("Vay 1 tỷ", EstimateSession())
    assert first.session.status == "collecting"
    assert first.session.amount == 1_000_000_000
    assert "thời hạn" in first.answer and "lãi suất" in first.answer
    asked = await case.execute("20 năm, 9%", first.session)
    assert asked.session.status == "collecting"
    assert "phương thức trả nợ" in asked.answer and "ưu đãi" in asked.answer
    second = await case.execute("Trả đều, không có ưu đãi", asked.session)
    assert second.session.status == "awaiting_confirmation"
    assert "9%/năm cố định toàn kỳ" in second.answer and "trả đều gốc + lãi" in second.answer
    assert calculator.calls == []
    third = await case.execute("Đổi thành 25 năm", second.session)
    assert third.session.status == "awaiting_confirmation"
    assert calculator.calls == []
    fourth = await case.execute("Xác nhận tính", third.session)
    assert fourth.session.status == "completed"
    assert len(calculator.calls) == 1 and calculator.calls[0].years == 25
    assert "1.234.567" in fourth.answer and "9.876.543" in fourth.answer
    assert "không phải đánh giá khả năng chi trả" in fourth.answer
    assert fourth.result == LoanEstimateResult(calculator.calls[0], 1234567, 9876543, "2026-10-31")


@pytest.mark.parametrize("action", ["unsupported", "cancel", "unrelated", "confirm"])
async def test_non_ready_or_unrelated_actions_never_call_backend(action):
    calculator = Calculator()
    case = EstimateLoanUseCase(Extractor(EstimateExtraction(action, {})), calculator, get_prompt_catalog())
    turn = await case.execute("message", EstimateSession())
    assert calculator.calls == []
    assert turn.handled is (action != "unrelated")


async def test_backend_error_is_not_rendered_as_success():
    case = EstimateLoanUseCase(
        Extractor(EstimateExtraction("confirm", {})), Calculator(LoanCalculationError()), get_prompt_catalog(),
    )
    with pytest.raises(LoanCalculationError):
        await case.execute("Xác nhận", EstimateSession(
            1_000_000_000, 20, Decimal("9"), "awaiting_confirmation", method="annuity", promo_duration_months=0,
        ))


class EstimateRepository(FakeRepository):
    def __init__(self, state=EstimateSession()):
        super().__init__()
        self.estimate_session = state

    async def claim(self, request, fingerprint):
        return ChatClaim("claimed", ChatSnapshot(0, (), uuid4(), uuid4(), self.estimate_session))

    async def commit(self, *args, **kwargs):
        self.committed_estimate = kwargs.get("estimate")
        result = await super().commit(*args, **kwargs)
        if self.state_update.estimate_session is not None:
            self.estimate_session = self.state_update.estimate_session
        return result


async def test_stream_estimate_multiturn_bypasses_rag_and_generation_and_classifies_once():
    classifier = StubIntentClassifier(ChatIntent.ESTIMATE)
    calculator = Calculator()
    completion = FakeCompletion()
    retrieval = FakeRetrieval(error=AssertionError("must not retrieve"))
    repository = EstimateRepository()
    case = StreamChatUseCase(
        completion, repository, prompts=get_prompt_catalog(), classifier=classifier, retrieval=retrieval,
        estimate=EstimateLoanUseCase(Extractor(
            EstimateExtraction("update", {"amount": 1_000_000_000}),
            EstimateExtraction("update", {
                "years": 20, "rate": Decimal("9"), "method": "annuity", "promo_duration_months": 0,
            }),
            EstimateExtraction("confirm", {}),
        ), calculator, get_prompt_catalog()),
    )
    for message in ["Vay 1 tỷ", "20 năm 9%", "Xác nhận tính"]:
        events = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), message, None))]
        assert events[-1].event == "done"
    assert len(classifier.calls) == 1
    assert completion.calls == 0 and retrieval.queries == []
    assert len(calculator.calls) == 1
    assert repository.estimate_session.status == "completed"
    assert repository.committed_estimate == LoanEstimateResult(
        calculator.calls[0], 1234567, 9876543, "2026-10-31",
    )
    assert events[-1].data["estimate"] is repository.committed_estimate


async def test_side_question_keeps_pending_estimate_without_running_calculator():
    state = EstimateSession(
        1_000_000_000, 20, Decimal("9"), "awaiting_confirmation", method="annuity", promo_duration_months=0,
    )
    repository = EstimateRepository(state)
    calculator = Calculator()
    classifier = StubIntentClassifier(ChatIntent.RETRIEVAL)
    case = StreamChatUseCase(
        FakeCompletion(), repository, prompts=get_prompt_catalog(), classifier=classifier,
        retrieval=FakeRetrieval(), estimate=EstimateLoanUseCase(
            Extractor(EstimateExtraction("unrelated", {})), calculator, get_prompt_catalog(),
        ),
    )
    events = [event async for event in case.execute(ChatRequest(uuid4(), uuid4(), "Hồ sơ cần gì?", None))]
    assert events[-1].event == "done"
    assert repository.estimate_session == state and calculator.calls == []
    assert repository.state_update.estimate_session is None
    assert repository.committed_estimate is None
    assert events[-1].data["estimate"] is None


@pytest.mark.parametrize("state", [
    EstimateSession(), EstimateSession(1_000_000_000, None, Decimal("0"), "collecting"),
    EstimateSession(
        1_000_000_000, 20, Decimal("8.5"), "awaiting_confirmation", method="annuity", promo_duration_months=0,
    ),
    EstimateSession(1_000_000_000, 20, Decimal("10"), "awaiting_confirmation", "reducing_balance",
                    Decimal("6.5"), 12),
    EstimateSession(None, None, None, "collecting", None, Decimal("6.5"), None),
])
def test_encrypted_profile_codec_roundtrips_and_supports_old_profiles(state):
    assert decode_estimate_session({}) == EstimateSession()
    assert decode_estimate_session({"estimate_session": encode_estimate_session(state)}) == state


@pytest.mark.parametrize("value", [[], {}, {"amount": -1, "years": 20, "rate": "9", "status": "collecting"}])
def test_corrupt_persisted_estimate_is_rejected(value):
    with pytest.raises(PayloadCipherError):
        decode_estimate_session({"estimate_session": value})


@pytest.mark.parametrize("content", [
    '[]', '{"action":"update","updates":{"years":20.5}}',
    '{"action":"update","updates":{"rate":"NaN"}}',
    '{"action":"confirm","updates":{"amount":1}}',
    '{"action":"update","updates":{"amount":true}}',
    '{"action":"update","updates":{"amount":null}}',
    '{"action":"update","updates":{"years":null}}',
    '{"action":"update","updates":{"unknown":1}}',
    '{"action":"update","updates":[],"extra":true}',
])
def test_extractor_rejects_invalid_structured_data(content):
    with pytest.raises(EstimateExtractionError):
        OpenAIEstimateExtractor._parse(content)


async def test_extractor_calls_provider_with_separate_prompt_and_structured_session():
    bodies = []

    async def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=completion_response(
            '{"action":"update","updates":{"rate":9.5}}',
        ))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenAIEstimateExtractor(
            base_url="http://provider.test/v1", api_key="test", model="test", prompts=get_prompt_catalog(),
        )
        with patch("app.infrastructure.llm.openai_estimate_extractor.AsyncOpenAI", side_effect=lambda **kwargs:
                   AsyncOpenAI(**kwargs, http_client=client)):
            result = await adapter.extract("9,5%", EstimateSession(1_000_000_000, 20, None, "collecting"))
    assert result.updates == {"rate": Decimal("9.5")}
    assert bodies[0]["messages"][0]["content"] == get_prompt_catalog().get("estimate_extraction")
    payload = json.loads(bodies[0]["messages"][1]["content"])
    assert payload["message"] == "9,5%" and payload["session"]["years"] == 20
    assert bodies[0]["response_format"] == {"type": "json_object"}


async def test_asks_method_and_promo_then_sends_them_to_backend():
    extractor = Extractor(
        EstimateExtraction("update", {"amount": 2_000_000_000, "years": 25}),
        EstimateExtraction("update", {"method": "reducing_balance", "promo_rate": Decimal("6.5")}),
        EstimateExtraction("update", {"promo_duration_months": 12}),
        EstimateExtraction("update", {"rate": Decimal("10")}),
        EstimateExtraction("confirm", {}),
    )
    calculator = Calculator()
    case = EstimateLoanUseCase(extractor, calculator, get_prompt_catalog())
    turn = await case.execute("Vay 2 tỷ 25 năm", EstimateSession())
    assert "phương thức trả nợ" in turn.answer and "ưu đãi" in turn.answer
    turn = await case.execute("Gốc đều, ưu đãi 6,5%", turn.session)
    assert turn.session.missing_fields == ("promo_duration_months", "rate")
    assert "số tháng hưởng lãi ưu đãi" in turn.answer
    turn = await case.execute("12 tháng", turn.session)
    assert "lãi suất sau ưu đãi" in turn.answer
    turn = await case.execute("sau đó 10%", turn.session)
    assert turn.session.status == "awaiting_confirmation" and calculator.calls == []
    assert "ưu đãi 6,5%/năm trong 12 tháng đầu, sau đó 10%/năm" in turn.answer
    assert "gốc trả đều, lãi tính trên dư nợ giảm dần" in turn.answer
    turn = await case.execute("Xác nhận tính", turn.session)
    assert calculator.calls == [LoanEstimateInput(
        2_000_000_000, 25, Decimal("10"), "reducing_balance", Decimal("6.5"), 12,
    )]
    assert "Khoản trả tháng đầu (cao nhất" in turn.answer and "1.234.567" in turn.answer
    assert "Hết thời gian ưu đãi" in turn.answer


async def test_promo_longer_than_term_is_asked_again():
    case = EstimateLoanUseCase(Extractor(
        EstimateExtraction("update", {"promo_rate": Decimal("5"), "promo_duration_months": 36}),
    ), Calculator(), get_prompt_catalog())
    session = EstimateSession(1_000_000_000, 2, None, "collecting", "annuity")
    turn = await case.execute("ưu đãi 5% 3 năm đầu", session)
    assert "36 tháng" in turn.answer and "2 năm" in turn.answer
    assert turn.session.promo_duration_months is None and turn.session.promo_rate == Decimal("5")


def test_session_promo_answers_can_change():
    session = EstimateSession().updated({"promo_rate": Decimal("6"), "promo_duration_months": 12})
    assert session.has_promo
    no_promo = session.updated({"promo_duration_months": 0})
    assert no_promo.promo_rate is None and "promo" not in no_promo.missing_fields
    again = no_promo.updated({"promo_rate": Decimal("5")})
    assert again.promo_duration_months is None and "promo_duration_months" in again.missing_fields


def test_legacy_profile_without_method_is_read_as_fixed_rate_annuity():
    legacy = {"amount": 1_000_000_000, "years": 20, "rate": "8.5", "status": "awaiting_confirmation"}
    session = decode_estimate_session({"estimate_session": legacy})
    assert session.to_input() == LoanEstimateInput(1_000_000_000, 20, Decimal("8.5"))


@pytest.mark.parametrize("kwargs", [
    {"method": "equal_principal"},
    {"promo_rate": Decimal("5")},
    {"promo_duration_months": 12},
    {"promo_rate": Decimal("5"), "promo_duration_months": 241},
    {"promo_rate": Decimal("-1"), "promo_duration_months": 12},
])
def test_estimate_input_rejects_invalid_method_or_promo(kwargs):
    with pytest.raises((ValueError, TypeError)):
        LoanEstimateInput(1_000_000_000, 20, Decimal("9"), **kwargs)


@pytest.mark.parametrize("content", [
    '{"action":"update","updates":{"method":"equal_principal"}}',
    '{"action":"update","updates":{"promo_rate":"6.5"}}',
    '{"action":"update","updates":{"promo_duration_months":12.5}}',
])
def test_extractor_rejects_invalid_method_or_promo(content):
    with pytest.raises(EstimateExtractionError):
        OpenAIEstimateExtractor._parse(content)


def test_done_event_estimate_carries_method_and_promo():
    request = LoanEstimateInput(1_500_000_000, 20, Decimal("10.3"), "annuity", Decimal("6.8"), 12)
    body = PostgresConversationRepository._serialize_estimate(
        LoanEstimateResult(request, 11_450_093, 1_977_234_734, "2026-10-31"),
    )
    assert body["method"] == "annuity" and body["promo_rate"] == 6.8 and body["promo_duration_months"] == 12
    assert body["rate"] == 10.3
