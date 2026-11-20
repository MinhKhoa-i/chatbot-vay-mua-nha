from decimal import Decimal

import httpx
import pytest

from app.domain.entities.bank_rank import BankRankRequest
from app.domain.ports.bank_ranker import BankRankError
from app.infrastructure.finance.http_bank_ranker import HttpBankRanker


def rank_payload(**overrides):
    payload = {
        "ranked": [{
            "id": "agribank",
            "short_name": "Agribank",
            "package_name": "Vay mua nhà ở thương mại",
            "total_cost": 466928374,
            "total_interest": 438579027,
            "prepay_fee": 28349347,
            "prepay_fee_known": True,
            "prepay_fee_is_upper_bound": False,
            "first_payment": 14475325,
            "floating_rate": 10.0,
            "floating_rate_assumed": True,
        }],
        "excluded": [{"id": "vpbank", "short_name": "VPBank", "reason": "Không phù hợp"}],
        "assumptions": {"floating_rate": 10.0},
        "updated_at": "2026-11-16",
        "is_sample": True,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def request_data():
    return BankRankRequest(
        amount=1_500_000_000,
        years=20,
        prepay_month=36,
        assumed_floating_rate=Decimal("10"),
    )


async def test_rank_posts_contract_and_parses_backend_numbers(request_data):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json=rank_payload())

    ranker = HttpBankRanker("http://backend.test/", transport=httpx.MockTransport(handler))
    result = await ranker.rank(request_data)

    assert str(requests[0].url) == "http://backend.test/api/banks/rank"
    assert requests[0].read() == (
        b'{"amount":1500000000,"years":20,"method":"annuity","grace_period_months":0,'
        b'"prepay_month":36,"property_value":null,"base_rate":null,"assumed_floating_rate":10.0}'
    )
    assert result.ranked[0].total_cost == 466928374
    assert result.ranked[0].floating_rate_assumed is True
    assert result.excluded[0].reason == "Không phù hợp"
    assert result.updated_at == "2026-11-16"


async def test_rank_preserves_unknown_total_cost(request_data):
    payload = rank_payload(ranked=[{
        **rank_payload()["ranked"][0],
        "total_cost": None,
        "prepay_fee": None,
        "prepay_fee_known": False,
    }])

    async def handler(_request):
        return httpx.Response(200, json=payload)

    result = await HttpBankRanker(
        "http://backend.test", transport=httpx.MockTransport(handler),
    ).rank(request_data)

    assert result.ranked[0].total_cost is None
    assert result.ranked[0].prepay_fee is None


async def test_rank_surfaces_vietnamese_422_detail(request_data):
    async def handler(_request):
        return httpx.Response(422, json={"detail": "Thời hạn vay không hợp lệ"})

    ranker = HttpBankRanker("http://backend.test", transport=httpx.MockTransport(handler))
    with pytest.raises(BankRankError) as caught:
        await ranker.rank(request_data)

    assert caught.value.code == "BANK_RANK_INVALID_INPUT"
    assert caught.value.detail == "Thời hạn vay không hợp lệ"
    assert caught.value.status_code == 422


@pytest.mark.parametrize(
    "exception,expected_code",
    [
        (httpx.ReadTimeout("timeout"), "BANK_RANK_TIMEOUT"),
        (httpx.ConnectError("offline"), "BANK_RANK_UNAVAILABLE"),
    ],
)
async def test_rank_maps_transport_failures(request_data, exception, expected_code):
    async def handler(request):
        raise exception

    ranker = HttpBankRanker("http://backend.test", transport=httpx.MockTransport(handler))
    with pytest.raises(BankRankError) as caught:
        await ranker.rank(request_data)

    assert caught.value.code == expected_code


async def test_rank_rejects_invalid_response(request_data):
    async def handler(_request):
        return httpx.Response(200, json={**rank_payload(), "ranked": "not-a-list"})

    ranker = HttpBankRanker("http://backend.test", transport=httpx.MockTransport(handler))
    with pytest.raises(BankRankError) as caught:
        await ranker.rank(request_data)

    assert caught.value.code == "BANK_RANK_INVALID_RESPONSE"
