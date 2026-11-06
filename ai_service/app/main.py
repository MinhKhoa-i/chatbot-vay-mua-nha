from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.db.session import dispose_database, get_async_session_factory
from app.presentation.api.v1.endpoints.routes import router as api_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Keep the engine alive for the app lifetime; fail startup when DB config is missing.
    get_async_session_factory()
    try:
        yield
    finally:
        await dispose_database()


app = FastAPI(
    title="Home Loan Chatbot API",
    version="0.1.0",
    description="Starter API for the home-loan guidance chatbot.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
