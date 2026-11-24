import json
from dataclasses import replace
from decimal import Decimal
from unittest.mock import patch

import httpx
import pytest
from openai import AsyncOpenAI

from app.application.use_cases.compare_banks import CompareBanksUseCase
from app.domain.entities.bank_compare_session import BankCompareExtraction, BankCompareSession
from app.domain.entities.bank_rank import BankRankResult, ExcludedBank, RankedBank
from app.domain.ports.bank_ranker import BankRankError
from app.domain.ports.bank_compare_extractor import BankCompareExtractionError
from app.domain.ports.prompt_catalog import PromptName
from app.infrastructure.llm.openai_bank_compare_extractor import OpenAIBankCompareExtractor
from app.infrastructure.prompts.loader import get_prompt_catalog
from test_llm_intent_classifier import completion_response


class Extractor:
    def __init__(self, *extractions):
        self.extractions = iter(extractions)
        self.calls = []
        self.last_assistant_messages = []

    async def extract(self, text, session, *, last_assistant_message=None):
        self.calls.append((text, session))
        self.last_assistant_messages.append(last_assistant_message)
        return next(self.extractions)


class Ranker:
    def __init__(self, result=None, error=None):
        self.calls = []
        self.result = result or BankRankResult((), (), {}, "2026-11-16", True)
        self.error = error

    async def rank(self, request):
        self.calls.append(request)
        if self.error:
            raise self.error
        return self.result


def ranked_bank(*, total_cost=466_928_374, prepay_fee=28_349_347):
    return RankedBank(
        id="agribank", short_name="Agribank", package_name="Vay mua nhà ở thương mại",
        total_cost=total_cost, total_interest=438_579_027, prepay_fee=prepay_fee,
        prepay_fee_known=prepay_fee is not None, prepay_fee_is_upper_bound=False,
        first_payment=14_475_325, floating_rate=Decimal("10"), floating_rate_assumed=True,
    )


@pytest.mark.asyncio
async def test_asks_for_assumed_rate_before_ranking():
    extractor = Extractor(
        BankCompareExtraction("update", {"amount": 1_500_000_000}),
        BankCompareExtraction("update", {"years": 20}),
        BankCompareExtraction("update", {"assumed_floating_rate": Decimal("10")}),
    )
    ranker = Ranker()
    case = CompareBanksUseCase(extractor, ranker, get_prompt_catalog())

    first = await case.execute("Vay 1,5 tỷ", BankCompareSession())
    second = await case.execute("20 năm", first.session)

    assert "thời hạn vay" in first.answer
    assert "Các ngân hàng chưa công bố lãi sau ưu đãi. Bạn muốn giả định lãi sau ưu đãi bao nhiêu %/năm để so sánh (ví dụ 10)?" in second.answer
    assert second.answer.count("lãi sau ưu đãi") == 2
    assert "mình cần bổ sung một số thông tin sau" not in second.answer
    assert "lãi sau ưu đãi giả định (%/năm)" not in second.answer
    assert second.session.years == 20
    assert second.session.assumed_floating_rate is None
    assert second.session.status == "collecting"
    assert ranker.calls == []

    third = await case.execute("10%/năm", second.session)

    assert third.session.assumed_floating_rate == Decimal("10")
    assert len(ranker.calls) == 1
    assert ranker.calls[0].assumed_floating_rate == Decimal("10")


@pytest.mark.asyncio
async def test_base_rate_does_not_require_assumed_floating_rate():
    ranker = Ranker()
    case = CompareBanksUseCase(
        Extractor(BankCompareExtraction("update", {
            "amount": 1_500_000_000, "years": 20, "base_rate": Decimal("7.5"),
        })),
        ranker,
        get_prompt_catalog(),
    )

    turn = await case.execute("So sánh khoản vay", BankCompareSession())

    assert len(ranker.calls) == 1
    assert ranker.calls[0].base_rate == Decimal("7.5")
    assert ranker.calls[0].assumed_floating_rate is None
    assert turn.session.status == "completed"


@pytest.mark.asyncio
async def test_complete_single_message_ranks_immediately_and_renders_backend_values():
    extractor = Extractor(BankCompareExtraction("update", {
        "amount": 1_500_000_000, "years": 20, "assumed_floating_rate": Decimal("10"),
    }))
    result = BankRankResult(
        (ranked_bank(),), (ExcludedBank("vpbank", "VPBank", "Không đủ thời hạn"),),
        {"floating_rate": Decimal("10")}, "2026-11-16", True,
    )
    ranker = Ranker(result)
    case = CompareBanksUseCase(extractor, ranker, get_prompt_catalog())

    turn = await case.execute("So sánh khoản vay 1,5 tỷ trong 20 năm, giả định lãi thả nổi 10%", BankCompareSession())

    assert len(ranker.calls) == 1
    assert ranker.calls[0].amount == 1_500_000_000
    assert ranker.calls[0].years == 20
    assert ranker.calls[0].assumed_floating_rate == Decimal("10")
    assert ranker.calls[0].grace_period_months == 0
    assert ranker.calls[0].base_rate is None
    assert turn.session.status == "completed"
    assert turn.result is result
    assert "Agribank" in turn.answer and "466.928.374" in turn.answer
    assert "14.475.325" in turn.answer and "2026-11-16" in turn.answer
    assert "VPBank: Không đủ thời hạn" in turn.answer
    assert "dữ liệu mẫu" in turn.answer
    assert "khoản trả tháng đầu 14.475.325 VND" in turn.answer
    assert "ngân hàng này giả định sử dụng lãi thả nổi 10%/năm" in turn.answer
    assert "phí trả trước 28.349.347 VND" in turn.answer
    assert "không phải khuyến nghị vay" in turn.answer


@pytest.mark.asyncio
async def test_unknown_total_cost_and_prepayment_fee_stay_unknown_in_answer():
    result = BankRankResult((ranked_bank(total_cost=None, prepay_fee=None),), (), {}, "2026-11-16", False)
    case = CompareBanksUseCase(
        Extractor(BankCompareExtraction("update", {
            "amount": 1_000_000_000, "years": 15, "assumed_floating_rate": Decimal("9"),
        })),
        Ranker(result), get_prompt_catalog(),
    )

    turn = await case.execute("So sánh vay 1 tỷ 15 năm, giả định lãi thả nổi 9%", BankCompareSession())

    assert "chưa xác định" in turn.answer
    assert "phí trả trước chưa rõ" in turn.answer
    assert "0 đồng" not in turn.answer


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["cancel", "unrelated"])
async def test_cancel_and_unrelated_actions_do_not_rank(action):
    initial = BankCompareSession(amount=1_000_000_000, years=20, status="collecting")
    ranker = Ranker()
    case = CompareBanksUseCase(Extractor(BankCompareExtraction(action, {})), ranker, get_prompt_catalog())

    turn = await case.execute("message", initial)

    assert ranker.calls == []
    if action == "cancel":
        assert turn.session == BankCompareSession()
        assert turn.answer == get_prompt_catalog().get(PromptName.BANK_COMPARE_CANCELLED)
    else:
        assert turn.handled is False and turn.session == initial


@pytest.mark.parametrize("content", [
    '[]', '{"action":"update","updates":{"years":20.5}}',
    '{"action":"update","updates":{"assumed_floating_rate":"NaN"}}',
    '{"action":"cancel","updates":{"amount":1}}',
    '{"action":"update","updates":{"amount":true}}',
    '{"action":"update","updates":{"amount":null}}',
    '{"action":"update","updates":{"unknown":1}}',
    '{"action":"update","updates":[],"extra":true}',
])
def test_extractor_rejects_invalid_structured_data(content):
    with pytest.raises(BankCompareExtractionError):
        OpenAIBankCompareExtractor._parse(content)


def test_extractor_parses_only_explicit_updates_and_preserves_session_fields():
    session = BankCompareSession(amount=1_000_000_000, status="collecting")
    extraction = OpenAIBankCompareExtractor._parse(
        '{"action":"update","updates":{"years":20,"assumed_floating_rate":9.5}}',
        session=session,
    )

    assert extraction == BankCompareExtraction("update", {
        "years": 20, "assumed_floating_rate": Decimal("9.5"),
    })


def test_extractor_accepts_grace_period_and_base_rate_updates():
    extraction = OpenAIBankCompareExtractor._parse(
        '{"action":"update","updates":{"grace_period_months":6,"base_rate":6.5}}',
    )

    assert extraction.updates == {
        "grace_period_months": 6, "base_rate": Decimal("6.5"),
    }


@pytest.mark.parametrize("rate", ["NaN", "Infinity", -1, True])
def test_extractor_rejects_invalid_base_rates(rate):
    import json

    content = json.dumps({"action": "update", "updates": {"base_rate": rate}})

    with pytest.raises(BankCompareExtractionError):
        OpenAIBankCompareExtractor._parse(content)


def test_extractor_rejects_null_grace_period_update_even_with_session():
    session = BankCompareSession(grace_period_months=6, status="collecting")

    with pytest.raises(BankCompareExtractionError):
        OpenAIBankCompareExtractor._parse(
            '{"action":"update","updates":{"grace_period_months":null}}',
            session=session,
        )


def test_extractor_rejects_updates_that_make_existing_session_invalid():
    session = BankCompareSession(years=20, grace_period_months=12, status="collecting")

    with pytest.raises(BankCompareExtractionError):
        OpenAIBankCompareExtractor._parse(
            '{"action":"update","updates":{"years":1}}',
            session=session,
        )


@pytest.mark.asyncio
async def test_result_formats_backend_assumptions_and_optional_scenario_details():
    bank = ranked_bank()
    result = BankRankResult(
        (bank,), (), {"floating_rate": Decimal("10")}, "2026-11-16", False,
    )
    case = CompareBanksUseCase(
        Extractor(BankCompareExtraction("update", {
            "amount": 1_000_000_000, "years": 15, "assumed_floating_rate": Decimal("9"),
            "grace_period_months": 6, "property_value": 2_000_000_000,
        })),
        Ranker(result), get_prompt_catalog(),
    )

    turn = await case.execute("so sánh", BankCompareSession())

    assert "floating_rate = 10%/năm" in turn.answer
    assert "ngân hàng này giả định sử dụng lãi thả nổi 10%/năm" in turn.answer
    assert "ân hạn gốc 6 tháng" in turn.answer
    assert "giá trị nhà 2.000.000.000 VND" in turn.answer


@pytest.mark.asyncio
async def test_result_marks_upper_bound_prepayment_fee_as_maximum():
    bank = replace(ranked_bank(), prepay_fee_is_upper_bound=True)
    result = BankRankResult((bank,), (), {}, "2026-11-16", False)
    case = CompareBanksUseCase(
        Extractor(BankCompareExtraction("update", {
            "amount": 1_000_000_000, "years": 15, "assumed_floating_rate": Decimal("9"),
        })),
        Ranker(result), get_prompt_catalog(),
    )

    turn = await case.execute("so sánh", BankCompareSession())

    assert "phí trả trước tối đa 28.349.347 VND" in turn.answer


@pytest.mark.asyncio
async def test_ranker_error_is_not_rendered_as_success():
    error = BankRankError("BANK_RANK_INVALID_INPUT", retryable=False, status_code=422, detail="Lỗi dữ liệu")
    case = CompareBanksUseCase(
        Extractor(BankCompareExtraction("update", {
            "amount": 1_000_000_000, "years": 20, "assumed_floating_rate": Decimal("9"),
        })),
        Ranker(error=error), get_prompt_catalog(),
    )

    with pytest.raises(BankRankError) as caught:
        await case.execute("So sánh khoản vay", BankCompareSession())

    assert caught.value is error




@pytest.mark.asyncio
async def test_result_template_renders_all_values():
    from app.infrastructure.prompts.loader import MarkdownPromptCatalog

    rendered = MarkdownPromptCatalog().get(PromptName.BANK_COMPARE_RESULT).format(
        amount="1", years=1, method_text="annuity", prepay_text="", grace_text="",
        property_text="", ranked_text="ranked", excluded_text="excluded",
        assumptions_text="assumptions", updated_at="2026-11-16", sample_note="",
    )

    assert "ranked" in rendered and "assumptions" in rendered


@pytest.mark.parametrize("content", [
    '{"action":"update","updates":{"grace_period_months":-1}}',
    '{"action":"update","updates":{"base_rate":"NaN"}}',
])
def test_extractor_rejects_invalid_bank_compare_fields(content):
    with pytest.raises(BankCompareExtractionError):
        OpenAIBankCompareExtractor._parse(content)


@pytest.mark.asyncio
async def test_provider_response_is_rejected_if_it_invalidates_session():
    session = BankCompareSession(years=20, grace_period_months=12, status="collecting")

    with pytest.raises(BankCompareExtractionError):
        OpenAIBankCompareExtractor._parse(
            '{"action":"update","updates":{"years":1}}', session=session,
        )



@pytest.mark.asyncio
async def test_extractor_sends_isolated_prompt_and_session_to_provider():
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json=completion_response(
            '{"action":"update","updates":{"amount":1500000000,"years":20,"assumed_floating_rate":10}}',
        ))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extractor = OpenAIBankCompareExtractor(
            base_url="http://provider.test/v1", api_key="test", model="test",
            prompts=get_prompt_catalog(),
        )
        with patch(
            "app.infrastructure.llm.openai_bank_compare_extractor.AsyncOpenAI",
            side_effect=lambda **kwargs: AsyncOpenAI(**kwargs, http_client=client),
        ):
            result = await extractor.extract("Vay 1,5 tỷ trong 20 năm, giả định lãi 10%", BankCompareSession())

    body = __import__("json").loads(requests[0].content)
    assert "không tự chọn, tra cứu hay suy ra tỷ lệ này" in body["messages"][0]["content"]
    assert "không bắt buộc" not in body["messages"][0]["content"]
    user_payload = json.loads(body["messages"][1]["content"])
    assert user_payload["message"] == "Vay 1,5 tỷ trong 20 năm, giả định lãi 10%"
    assert user_payload["missing_fields"] == ["amount", "years", "assumed_floating_rate"]
    assert "last_assistant_message" not in user_payload
    assert result.updates == {
        "amount": 1_500_000_000, "years": 20, "assumed_floating_rate": Decimal("10"),
    }


@pytest.mark.asyncio
async def test_extractor_sends_missing_fields_and_last_assistant_message_for_short_rate_reply():
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json=completion_response(
            '{"action":"update","updates":{"assumed_floating_rate":5}}',
        ))

    session = BankCompareSession(amount=1_500_000_000, years=20, status="collecting")
    prompt_question = (
        "Các ngân hàng chưa công bố lãi sau ưu đãi. Bạn muốn giả định lãi sau ưu đãi "
        "bao nhiêu %/năm để so sánh (ví dụ 10)?"
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        extractor = OpenAIBankCompareExtractor(
            base_url="http://provider.test/v1", api_key="test", model="test",
            prompts=get_prompt_catalog(),
        )
        with patch(
            "app.infrastructure.llm.openai_bank_compare_extractor.AsyncOpenAI",
            side_effect=lambda **kwargs: AsyncOpenAI(**kwargs, http_client=client),
        ):
            result = await extractor.extract("5%", session, last_assistant_message=prompt_question)

    body = json.loads(requests[0].content)
    system_prompt = body["messages"][0]["content"]
    user_payload = json.loads(body["messages"][1]["content"])
    assert "missing_fields" in system_prompt
    assert "last_assistant_message" in system_prompt
    assert "5%" in system_prompt
    assert user_payload["missing_fields"] == ["assumed_floating_rate"]
    assert user_payload["last_assistant_message"] == prompt_question
    assert user_payload["message"] == "5%"
    assert result == BankCompareExtraction("update", {"assumed_floating_rate": Decimal("5")})
