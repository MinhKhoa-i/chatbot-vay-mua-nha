import logging
from functools import lru_cache

from fastapi import HTTPException

from app.application.services.knowledge_retrieval import KnowledgeRetrievalService
from app.application.use_cases.stream_chat import StreamChatUseCase
from app.application.use_cases.estimate_loan import EstimateLoanUseCase
from app.infrastructure.finance.http_loan_calculator import HttpLoanCalculator
from app.infrastructure.llm.openai_estimate_extractor import OpenAIEstimateExtractor
from app.core.config import get_settings
from app.domain.errors import ChatConfigurationError, ChatError
from app.infrastructure.db.conversation_repository import PostgresConversationRepository
from app.infrastructure.db.session import get_async_session_factory
from app.infrastructure.knowledge.postgres_knowledge_repository import PostgresKnowledgeRepository
from app.infrastructure.knowledge.qwen_embedding_adapter import QwenEmbeddingAdapter
from app.infrastructure.llm.openai_chat_adapter import OpenAIChatAdapter
from app.infrastructure.llm.openai_intent_classifier import OpenAIIntentClassifier
from app.infrastructure.prompts.loader import get_prompt_catalog
from app.presentation.api.conversation_dependencies import _get_cipher

logger = logging.getLogger(__name__)


@lru_cache
def get_stream_chat_use_case() -> StreamChatUseCase:
    try:
        return _build_stream_chat_use_case()
    except ChatError as exc:
        logger.exception("Chat initialization failed (code=%s, stage=%s)", exc.code, exc.stage)
        raise HTTPException(status_code=exc.status_code, detail=exc.public_payload()) from exc
    except Exception as exc:
        logger.exception("Unexpected chat initialization failure")
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "retryable": False}) from exc


def _build_stream_chat_use_case() -> StreamChatUseCase:
    try:
        settings = get_settings()
    except (RuntimeError, ValueError) as exc:
        raise ChatConfigurationError("CONFIGURATION_INVALID", stage="configuration") from exc
    prompts = get_prompt_catalog()
    try:
        sessions = get_async_session_factory()
    except (RuntimeError, ValueError) as exc:
        raise ChatConfigurationError("DATABASE_NOT_CONFIGURED", stage="database_configuration") from exc
    try:
        cipher = _get_cipher()
    except (RuntimeError, ValueError) as exc:
        raise ChatConfigurationError("ENCRYPTION_NOT_CONFIGURED", stage="encryption_configuration") from exc
    try:
        embedder = QwenEmbeddingAdapter(
            base_url=settings.embedding_base_url, api_key=settings.embedding_api_key,
            model=settings.embedding_model, dimensions=settings.embedding_dimensions,
            source_dimensions=4096,
        )
    except ValueError as exc:
        raise ChatConfigurationError("EMBEDDING_CONFIGURATION_INVALID", stage="embedding_configuration") from exc
    return StreamChatUseCase(
        OpenAIChatAdapter(
            base_url=settings.llm_base_url, api_key=settings.llm_api_key,
            model=settings.llm_model, timeout_seconds=min(settings.llm_timeout_seconds, 45.0),
            prompts=prompts,
        ),
        PostgresConversationRepository(sessions, cipher), prompts=prompts,
        classifier=OpenAIIntentClassifier(
            base_url=settings.llm_base_url, api_key=settings.llm_api_key,
            model=settings.llm_model, timeout_seconds=min(settings.llm_timeout_seconds, 10.0),
            prompts=prompts,
        ),
        retrieval=KnowledgeRetrievalService(PostgresKnowledgeRepository(sessions), embedder),
        estimate=EstimateLoanUseCase(
            OpenAIEstimateExtractor(
                base_url=settings.llm_base_url, api_key=settings.llm_api_key,
                model=settings.llm_model, prompts=prompts,
                timeout_seconds=min(settings.llm_timeout_seconds, 10.0),
            ),
            HttpLoanCalculator(settings.loan_backend_base_url), prompts,
        ),
    )
