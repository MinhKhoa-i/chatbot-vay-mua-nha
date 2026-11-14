"""Kiểm tra hợp đồng API trong docs/api.md."""
import json
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import SAMPLE_REPLY, app
from finance.calculator import max_loan, monthly_payment, total_interest

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


# --- Hạn mức vay tối đa (STT 17 tuần 2) ---
def test_estimate_khong_gui_gia_tri_nha_thi_max_loan_null():
    body = client.post("/api/estimate", json={"amount": 1_500_000_000, "years": 20}).json()
    assert body["max_loan"] is None


def test_estimate_tra_han_muc_vay_toi_da_dung_calculator():
    body = client.post("/api/estimate", json={
        "amount": 1_500_000_000, "years": 20, "rate": 9.2,
        "promo_rate": 5.2, "promo_duration_months": 12,
        "property_value": 3_000_000_000, "monthly_income": 40_000_000,
        "existing_monthly_debt": 2_000_000, "max_ltv_percent": 70,
    }).json()
    expected = max_loan(3_000_000_000, 40_000_000, 240, 9.2, "annuity", 5.2, 12,
                        existing_monthly_debt=2_000_000, max_ltv=70, max_dti=0.5)
    limit = body["max_loan"]
    assert {k: limit[k] for k in expected} == expected
    assert limit["max_ltv_percent"] == 70 and limit["max_dti_percent"] == 50
    assert limit["max_loan"] == min(limit["by_ltv"], limit["by_dti"])
    assert limit["by_ltv"] == 2_100_000_000  # 70% giá trị nhà


def test_estimate_han_muc_bi_gioi_han_boi_thu_nhap():
    limit = client.post("/api/estimate", json={
        "amount": 1_000_000_000, "years": 20,
        "property_value": 10_000_000_000, "monthly_income": 20_000_000,
    }).json()["max_loan"]
    assert limit["limited_by"] == "dti" and limit["max_loan"] == limit["by_dti"]


@pytest.mark.parametrize("payload", [
    {"property_value": 3_000_000_000},                       # thiếu thu nhập
    {"monthly_income": 40_000_000},                          # thiếu giá trị nhà
    {"property_value": 3e9, "monthly_income": 4e7, "max_ltv_percent": 0},
    {"property_value": 3e9, "monthly_income": 4e7, "max_dti_percent": 120},
    {"property_value": 3e9, "monthly_income": 4e7, "existing_monthly_debt": -1},
])
def test_estimate_han_muc_dau_vao_sai(payload):
    res = client.post("/api/estimate", json={"amount": 1_000_000_000, "years": 20, **payload})
    assert res.status_code == 422


def test_estimate_thieu_mot_trong_hai_thi_bao_cau_tieng_viet():
    res = client.post("/api/estimate", json={"amount": 1e9, "years": 20, "monthly_income": 40_000_000})
    assert isinstance(res.json()["detail"], str)


# ---------------------------------------------------------------------------
# /api/chat nối ai_service (STT 16, docs/api.md mục 5)
# Không gọi ai_service thật: thay transport của httpx bằng MockTransport.
# ---------------------------------------------------------------------------
AI_URL = "http://ai.test"
SESSION = "2dd4d22a-993d-4a2e-b544-91409ebfb17b"


def sse(*events):
    """Ghép các event thành nội dung text/event-stream."""
    return "".join(f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                   for name, data in events)


def done(reply="Xin chào bạn", estimate=None):
    return ("done", {"conversation_id": SESSION, "client_request_id": "x",
                     "conversation_version": 1, "reply": reply, "estimate": estimate})


@pytest.fixture
def ai(monkeypatch):
    """Giả lập ai_service. Gán `ai.responses` là danh sách câu trả lời theo thứ tự;
    mỗi phần tử là chuỗi SSE, số mã HTTP, hoặc một exception của httpx."""
    class Fake:
        responses: list = []
        requests: list = []
        sleeps: list = []

    def handler(request: httpx.Request):
        Fake.requests.append(request)
        item = Fake.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, int):
            return httpx.Response(item, json={"detail": "loi"})
        return httpx.Response(200, text=item, headers={"content-type": "text/event-stream"})

    Fake.responses, Fake.requests, Fake.sleeps = [], [], []
    monkeypatch.setenv("AI_SERVICE_URL", AI_URL + "/")
    monkeypatch.setattr(main_module, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(main_module, "_sleep", Fake.sleeps.append)
    return Fake


def ask_chat(message="Hồ sơ vay gồm gì?", session_id=SESSION):
    return client.post("/api/chat", json={"message": message, "session_id": session_id})


def test_chua_dat_ai_service_url_thi_tra_cau_mau(monkeypatch):
    monkeypatch.delenv("AI_SERVICE_URL", raising=False)
    body = ask_chat().json()
    assert body["reply"] == SAMPLE_REPLY and body["estimate"] is None


def test_doc_sse_lay_reply_trong_done(ai):
    ai.responses = [sse(("delta", {"text": "Xin"}), ("delta", {"text": " chào"}), done("Xin chào bạn"))]
    res = ask_chat()
    assert res.status_code == 200
    assert res.json()["reply"] == "Xin chào bạn"
    assert set(res.json()) == {"reply", "updated_at", "estimate"}

    req = ai.requests[0]
    assert req.url == f"{AI_URL}/api/v1/conversations/{SESSION}/messages"
    payload = json.loads(req.content)
    assert payload["text"] == "Hồ sơ vay gồm gì?"
    assert UUID(payload["client_request_id"]).version == 4


def test_loi_retryable_thi_thu_lai_cung_client_request_id(ai):
    ai.responses = [sse(("error", {"code": "CONVERSATION_BUSY", "retryable": True, "retry_after": 1})),
                    sse(done("Đã xong"))]
    assert ask_chat().json()["reply"] == "Đã xong"
    ids = [json.loads(r.content)["client_request_id"] for r in ai.requests]
    assert len(ids) == 2 and ids[0] == ids[1]
    assert ai.sleeps == [1.0]


def test_loi_mang_va_5xx_cung_duoc_thu_lai(ai):
    ai.responses = [httpx.ConnectError("mat ket noi"), 503, sse(done("Ổn rồi"))]
    assert ask_chat().json()["reply"] == "Ổn rồi"
    assert len(ai.requests) == 3


def test_loi_khong_retryable_thi_bao_502_ngay(ai):
    ai.responses = [sse(("error", {"code": "MODEL_NOT_CONFIGURED", "retryable": False}))]
    res = ask_chat()
    assert res.status_code == 502 and isinstance(res.json()["detail"], str)
    assert len(ai.requests) == 1


def test_thu_lai_het_so_lan_thi_bao_502(ai):
    ai.responses = [sse(("error", {"code": "MODEL_TIMEOUT", "retryable": True}))] * main_module.AI_MAX_ATTEMPTS
    assert ask_chat().status_code == 502
    assert len(ai.requests) == main_module.AI_MAX_ATTEMPTS


def test_luong_ket_thuc_khong_co_done_thi_thu_lai(ai):
    ai.responses = [sse(("delta", {"text": "dang tra loi"})), sse(done("Hoàn tất"))]
    assert ask_chat().json()["reply"] == "Hoàn tất"


def test_session_id_khong_phai_uuid_van_giu_ngu_canh(ai):
    ai.responses = [sse(done()), sse(done())]
    ask_chat(session_id="phien-1")
    ask_chat(session_id="phien-1")
    paths = [r.url.path for r in ai.requests]
    assert paths[0] == paths[1]
    UUID(paths[0].split("/")[4])  # là UUID hợp lệ
