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
from app.domain.entities.loan_estimate import LoanEstimateResult
from app.domain.ports.estimate_extractor import EstimateExtractionError
from app.domain.ports.loan_calculator import LoanCalculationError
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
        EstimateExtraction("update", {"years": 25}),
        EstimateExtraction("confirm", {}),
    )
    calculator = Calculator()
    case = EstimateLoanUseCase(extractor, calculator, get_prompt_catalog())
    first = await case.execute("Vay 1 tỷ", EstimateSession())
    assert first.session.status == "collecting"
    assert first.session.amount == 1_000_000_000
    assert "thời hạn" in first.answer and "lãi suất" in first.answer
    second = await case.execute("20 năm, 9%", first.session)
    assert second.session.status == "awaiting_confirmation"
    assert calculator.calls == []
    third = await case.execute("Đổi thành 25 năm", second.session)
    assert third.session.status == "awaiting_confirmation"
    assert calculator.calls == []
    fourth = await case.execute("Xác nhận tính", third.session)
    assert fourth.session.status == "completed"
    assert len(calculator.calls) == 1 and calculator.calls[0].years == 25
    assert "1.234.567" in fourth.answer and "9.876.543" in fourth.answer
    assert "không phải đánh giá khả năng chi trả" in fourth.answer


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
        await case.execute("Xác nhận", EstimateSession(1_000_000_000, 20, Decimal("9"), "awaiting_confirmation"))


class EstimateRepository(FakeRepository):
    def __init__(self, state=EstimateSession()):
        super().__init__()
        self.estimate_session = state

    async def claim(self, request, fingerprint):
        return ChatClaim("claimed", ChatSnapshot(0, (), uuid4(), uuid4(), self.estimate_session))

    async def commit(self, *args, **kwargs):
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
            EstimateExtraction("update", {"years": 20, "rate": Decimal("9")}),
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


async def test_side_question_keeps_pending_estimate_without_running_calculator():
    state = EstimateSession(1_000_000_000, 20, Decimal("9"), "awaiting_confirmation")
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


@pytest.mark.parametrize("state", [
    EstimateSession(), EstimateSession(1_000_000_000, None, Decimal("0"), "collecting"),
    EstimateSession(1_000_000_000, 20, Decimal("8.5"), "awaiting_confirmation"),
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
