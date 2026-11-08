import json
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from finance.calculator import ANNUITY, schedule

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


@app.post("/api/chat")
def chat(req: ChatRequest):
    # Dữ liệu giả trả lời theo mẫu cố định (chưa nối ai_service, xem docs/api.md mục 5)
    return {
        "reply": "Quy trình vay mua nhà gồm 5 giai đoạn: chuẩn bị hồ sơ, thẩm định, "
                 "phê duyệt, ký hợp đồng và giải ngân, trả nợ. (dữ liệu mẫu)",
        "updated_at": DATA_UPDATED,
        "estimate": None,
    }


# /api/estimate: dùng chung backend/finance/calculator.py, không tự tính lại
class EstimateRequest(BaseModel):
    amount: int = Field(gt=0, description="Số tiền vay (VND, số nguyên)")
    years: int = Field(gt=0, le=35)
    rate: float = Field(8.5, ge=0, description="Lãi suất %/năm (sau ưu đãi nếu có ưu đãi)")
    method: Literal["annuity", "reducing_balance"] = ANNUITY
    promo_rate: Optional[float] = Field(None, ge=0, description="Lãi ưu đãi %/năm")
    promo_duration_months: int = Field(0, ge=0, description="Số tháng ưu đãi")


@app.post("/api/estimate")
def estimate(req: EstimateRequest):
    try:
        rows = schedule(req.amount, req.years * 12, req.rate, req.method,
                        req.promo_rate, req.promo_duration_months)
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
