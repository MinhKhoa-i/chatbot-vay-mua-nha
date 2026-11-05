from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DATA_UPDATED = "2026-10-31"

app = FastAPI(title="Chatbot vay mua nhà API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# /api/chat
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@app.post("/api/chat")
def chat(req: ChatRequest):
    # Dữ liệu giả trả lời theo mẫu cố định
    return {
        "reply": "Quy trình vay mua nhà gồm 5 giai đoạn: chuẩn bị hồ sơ, thẩm định, "
                 "phê duyệt, ký hợp đồng và giải ngân, trả nợ. (dữ liệu mẫu)",
        "updated_at": DATA_UPDATED,
        "estimate": None,
    }


# /api/estimate 
class EstimateRequest(BaseModel):
    amount: float = Field(gt=0, description="Số tiền vay (VND)")
    years: int = Field(gt=0, le=35)
    rate: float = Field(8.5, ge=0, description="Lãi suất %/năm")


@app.post("/api/estimate")
def estimate(req: EstimateRequest):
    n = req.years * 12
    r = req.rate / 100 / 12
    monthly = req.amount / n if r == 0 else req.amount * r / (1 - (1 + r) ** -n)
    return {
        "amount": req.amount,
        "years": req.years,
        "rate": req.rate,
        "monthly_payment": round(monthly),
        "total_interest": round(monthly * n - req.amount),
        "method": "annuity",
        "updated_at": DATA_UPDATED,
    }


BANKS = [  # SỐ LIỆU GIẢ để test giao diện
    {"id": "bank-a", "name": "Ngân hàng A (mẫu)", "promo_rate": 6.5, "promo_months": 12,
     "floating_margin": 3.5, "max_ltv": 70, "max_years": 25},
    {"id": "bank-b", "name": "Ngân hàng B (mẫu)", "promo_rate": 7.2, "promo_months": 24,
     "floating_margin": 3.0, "max_ltv": 75, "max_years": 30},
    {"id": "bank-c", "name": "Ngân hàng C (mẫu)", "promo_rate": 5.9, "promo_months": 6,
     "floating_margin": 4.0, "max_ltv": 70, "max_years": 20},
]


@app.get("/api/banks")
def banks():
    return {"banks": BANKS, "updated_at": DATA_UPDATED, "is_sample": True}
