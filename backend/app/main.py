import json
import logging
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from finance.calculator import ANNUITY, max_loan, schedule

logger = logging.getLogger(__name__)

# Hợp đồng API: xem docs/api.md
DATA_UPDATED = "2026-10-31"
BANKS_FILE = Path(__file__).resolve().parents[2] / "data" / "banks_sample.json"

app = FastAPI(title="Chatbot vay mua nhà API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# /api/chat
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Nối /api/chat với ai_service (docs/api.md mục 5)
#   Backend gửi POST {AI_SERVICE_URL}/api/v1/conversations/{conversation_id}/messages
#   rồi đọc SSE (delta, done, error) tới event `done` và lấy `reply`.
#   - Lỗi `retryable`, lỗi mạng, hết giờ, HTTP 5xx: thử lại với CÙNG client_request_id.
#   - Chưa đặt AI_SERVICE_URL: giữ câu trả lời mẫu.
# ---------------------------------------------------------------------------
AI_DEFAULT_TIMEOUT = 60.0     # giây chờ ai_service trả lời (LLM có thể chậm)
AI_MAX_ATTEMPTS = 3           # tổng số lần gửi, kể cả lần đầu
SESSION_NAMESPACE = uuid5(NAMESPACE_URL, "chatbot-vay-mua-nha/session")

# Cho phép test thay thế (không phải chờ thật, không gọi mạng thật)
_sleep = time.sleep
_transport: httpx.BaseTransport | None = None


class AIServiceError(Exception):
    def __init__(self, code: str, retryable: bool = False):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


def conversation_id(session_id: str | None) -> str:
    """ai_service cần UUID trong đường dẫn.

    session_id đã là UUID (frontend dùng crypto.randomUUID) thì giữ nguyên;
    chuỗi khác thì đổi thành UUID cố định theo chuỗi đó để vẫn giữ được ngữ cảnh;
    không có session_id thì tạo cuộc trò chuyện mới.
    """
    if not session_id:
        return str(uuid4())
    try:
        return str(UUID(session_id))
    except ValueError:
        return str(uuid5(SESSION_NAMESPACE, session_id))


def _iter_events(response: httpx.Response):
    """Tách luồng SSE thành các cặp (tên event, dữ liệu JSON)."""
    event, data = None, []
    for line in response.iter_lines():
        if line == "":
            if event and data:
                yield event, json.loads("\n".join(data))
            event, data = None, []
        elif line.startswith("event:"):
            event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data.append(line[len("data:"):].strip())
    if event and data:  # luồng kết thúc mà không có dòng trống cuối
        yield event, json.loads("\n".join(data))


def _send_once(client: httpx.Client, url: str, payload: dict) -> dict:
    """Gửi một lần, trả về dữ liệu event `done`."""
    try:
        with client.stream("POST", url, json=payload,
                           headers={"Accept": "text/event-stream"}) as response:
            if response.status_code >= 500:
                raise AIServiceError(f"HTTP_{response.status_code}", retryable=True)
            if response.status_code >= 400:
                raise AIServiceError(f"HTTP_{response.status_code}", retryable=False)
            for event, data in _iter_events(response):
                if event == "done":
                    return data
                if event == "error":
                    error = AIServiceError(str(data.get("code", "UNKNOWN")),
                                           retryable=bool(data.get("retryable")))
                    error.retry_after = data.get("retry_after")
                    raise error
                # `delta` là chữ tạm thời, chỉ dùng `reply` trong `done`
    except httpx.TimeoutException as exc:
        raise AIServiceError("AI_SERVICE_TIMEOUT", retryable=True) from exc
    except httpx.RequestError as exc:
        raise AIServiceError("AI_SERVICE_UNAVAILABLE", retryable=True) from exc
    except (json.JSONDecodeError, AttributeError) as exc:
        raise AIServiceError("AI_SERVICE_INVALID_RESPONSE", retryable=False) from exc
    raise AIServiceError("AI_SERVICE_NO_DONE", retryable=True)


def ask_ai_service(message: str, session_id: str | None, base_url: str,
        timeout: float | None = None, max_attempts: int = AI_MAX_ATTEMPTS) -> dict:
    """Hỏi ai_service, trả về dữ liệu event `done` (có `reply`, `estimate`...)."""
    if timeout is None:
        timeout = float(os.getenv("AI_SERVICE_TIMEOUT", AI_DEFAULT_TIMEOUT))
    url = f"{base_url}/api/v1/conversations/{conversation_id(session_id)}/messages"
    payload = {"client_request_id": str(uuid4()), "text": message}  # giữ nguyên khi thử lại

    with httpx.Client(timeout=httpx.Timeout(timeout, connect=5.0), transport=_transport) as client:
        for attempt in range(1, max_attempts + 1):
            try:
                done = _send_once(client, url, payload)
            except AIServiceError as exc:
                if not exc.retryable or attempt == max_attempts:
                    raise
                wait = getattr(exc, "retry_after", None)
                _sleep(float(wait) if isinstance(wait, (int, float)) else attempt)
                continue
            if not isinstance(done.get("reply"), str):
                raise AIServiceError("AI_SERVICE_INVALID_RESPONSE")
            return done
    raise AIServiceError("AI_SERVICE_RETRY_EXHAUSTED")  # không tới được đây


def ai_service_url() -> Optional[str]:
    """Đọc AI_SERVICE_URL mỗi lần gọi; để trống nghĩa là chưa nối ai_service."""
    url = os.getenv("AI_SERVICE_URL", "").strip()
    return url.rstrip("/") or None


SAMPLE_REPLY = ("Quy trình vay mua nhà gồm 5 giai đoạn: chuẩn bị hồ sơ, thẩm định, "
                "phê duyệt, ký hợp đồng và giải ngân, trả nợ. (dữ liệu mẫu)")
AI_ERROR_DETAIL = "Trợ lý AI đang bận hoặc chưa sẵn sàng, bạn vui lòng thử lại sau ít phút."


@app.post("/api/chat")
def chat(req: ChatRequest):
    base_url = ai_service_url()
    if base_url is None:
        # Chưa đặt AI_SERVICE_URL: giữ câu trả lời mẫu (docs/api.md mục 5)
        return {"reply": SAMPLE_REPLY, "updated_at": DATA_UPDATED, "estimate": None}
    try:
        done = ask_ai_service(req.message, req.session_id, base_url)
    except AIServiceError as exc:
        logger.warning("ai_service lỗi: %s (retryable=%s)", exc.code, exc.retryable)
        raise HTTPException(status_code=502, detail=AI_ERROR_DETAIL) from exc
    return {"reply": done["reply"], "updated_at": DATA_UPDATED, "estimate": None}


# /api/estimate: dùng chung backend/finance/calculator.py, không tự tính lại
class EstimateRequest(BaseModel):
    amount: int = Field(gt=0, description="Số tiền vay (VND, số nguyên)")
    years: int = Field(gt=0, le=35)
    rate: float = Field(8.5, ge=0, description="Lãi suất %/năm (sau ưu đãi nếu có ưu đãi)")
    method: Literal["annuity", "reducing_balance"] = ANNUITY
    promo_rate: Optional[float] = Field(None, ge=0, description="Lãi ưu đãi %/năm")
    promo_duration_months: int = Field(0, ge=0, description="Số tháng ưu đãi")
    # Hạn mức vay tối đa (không bắt buộc): gửi đủ giá trị nhà và thu nhập thì backend tính thêm
    property_value: Optional[int] = Field(None, gt=0, description="Giá trị nhà / tài sản bảo đảm (VND)")
    monthly_income: Optional[int] = Field(None, gt=0, description="Thu nhập ròng hằng tháng (VND)")
    existing_monthly_debt: int = Field(0, ge=0, description="Nợ khác phải trả hằng tháng (VND)")
    max_ltv_percent: float = Field(80, gt=0, le=100, description="Tỷ lệ cho vay tối đa / giá trị nhà (%)")
    max_dti_percent: float = Field(50, gt=0, le=100, description="Tỷ lệ trả nợ tối đa / thu nhập (%)")


def _max_loan(req: EstimateRequest) -> Optional[dict]:
    """Gọi max_loan() của calculator.py; thiếu giá trị nhà và thu nhập thì trả None."""
    if req.property_value is None and req.monthly_income is None:
        return None
    if req.property_value is None or req.monthly_income is None:
        raise ValueError("Cần nhập cả giá trị nhà và thu nhập hằng tháng để tính hạn mức vay tối đa")
    result = max_loan(req.property_value, req.monthly_income, req.years * 12, req.rate,
                      req.method, req.promo_rate, req.promo_duration_months,
                      existing_monthly_debt=req.existing_monthly_debt,
                      max_ltv=req.max_ltv_percent / 100, max_dti=req.max_dti_percent / 100)
    return {**result, "max_ltv_percent": float(req.max_ltv_percent),
            "max_dti_percent": float(req.max_dti_percent)}


@app.post("/api/estimate")
def estimate(req: EstimateRequest):
    try:
        rows = schedule(req.amount, req.years * 12, req.rate, req.method,
                        req.promo_rate, req.promo_duration_months)
        limit = _max_loan(req)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "amount": req.amount,
        "years": req.years,
        "rate": req.rate,
        "method": req.method,
        "promo_rate": req.promo_rate,
        "promo_duration_months": req.promo_duration_months,
        "monthly_payment": rows[0]["payment"],  # tháng đầu (gốc đều: tháng cao nhất)
        "total_interest": sum(r["interest"] for r in rows),
        "max_loan": limit,
        "updated_at": DATA_UPDATED,
    }


# /api/banks: đọc dữ liệu mẫu do nhóm Dữ liệu nhập tay (docs/schema.md)
@lru_cache(maxsize=1)
def _load_banks() -> dict:
    with BANKS_FILE.open(encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/banks")
def banks():
    data = _load_banks()
    return {
        "banks": data["banks"],
        "updated_at": data.get("updated_at", DATA_UPDATED),
        "is_sample": True,
    }
