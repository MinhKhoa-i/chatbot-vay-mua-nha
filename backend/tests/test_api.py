"""Kiểm tra hợp đồng API trong docs/api.md."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from finance.calculator import monthly_payment, total_interest

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_chat_contract():
    body = client.post("/api/chat", json={"message": "quy trình vay", "session_id": "1"}).json()
    assert set(body) == {"reply", "updated_at", "estimate"}
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_estimate_dung_calculator():
    body = client.post("/api/estimate", json={"amount": 1_500_000_000, "years": 20}).json()
    assert body["method"] == "annuity" and body["rate"] == 8.5
    assert body["monthly_payment"] == monthly_payment(1_500_000_000, 240, 8.5)
    assert body["total_interest"] == total_interest(1_500_000_000, 240, 8.5)
    # Các trường ai_service (HttpLoanCalculator) bắt buộc phải có
    for key in ("amount", "years", "rate", "method", "monthly_payment", "total_interest", "updated_at"):
        assert key in body


def test_estimate_goc_deu_va_uu_dai():
    body = client.post("/api/estimate", json={
        "amount": 1_000_000_000, "years": 20, "rate": 10, "method": "reducing_balance",
        "promo_rate": 7, "promo_duration_months": 12,
    }).json()
    assert body["monthly_payment"] == monthly_payment(1_000_000_000, 240, 10, "reducing_balance", 7, 12)


@pytest.mark.parametrize("payload", [
    {"amount": 0, "years": 20},
    {"amount": 1e9, "years": 36},
    {"amount": 1e9, "years": 20, "method": "equal_principal"},
    {"amount": 1e9, "years": 20, "promo_rate": 7},            # thiếu số tháng ưu đãi
    {"amount": 1e9, "years": 1, "promo_rate": 7, "promo_duration_months": 24},
])
def test_estimate_dau_vao_sai(payload):
    assert client.post("/api/estimate", json=payload).status_code == 422


def test_banks_theo_schema():
    body = client.get("/api/banks").json()
    assert body["is_sample"] is True and body["updated_at"]
    assert len(body["banks"]) >= 2
    for bank in body["banks"]:
        assert {"promo_rate", "promo_duration_months", "floating_margin"} <= set(bank["interest_rate"])
        assert {"max_ltv_percent", "max_loan_term_years"} <= set(bank["loan_limit"])
        assert set(bank["repayment_methods"]) <= {"annuity", "reducing_balance"}
