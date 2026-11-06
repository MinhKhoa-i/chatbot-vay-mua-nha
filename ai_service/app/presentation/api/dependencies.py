from functools import lru_cache

from app.application.use_cases.chat import ChatUseCase
from app.domain.entities.chat_message import Intent
from app.infrastructure.chat.annuity_loan_calculator import AnnuityLoanCalculator
from app.infrastructure.chat.in_memory_chat_state_store import InMemoryChatStateStore
from app.infrastructure.chat.keyword_intent_handler import KeywordIntentHandler
from app.infrastructure.chat.json_knowledge_retriever import JsonKnowledgeRetriever
from app.infrastructure.chat.retrieval_chat_responder import RetrievalChatResponder
from app.infrastructure.chat.rule_based_intent_classifier import RuleBasedIntentClassifier
from app.infrastructure.db.session import get_async_session_factory as _get_async_session_factory


@lru_cache
def get_chat_use_case() -> ChatUseCase:
    """Composition root: bind domain ports to replaceable infrastructure adapters."""
    return ChatUseCase(
        classifier=RuleBasedIntentClassifier(),
        handlers=(
            KeywordIntentHandler(Intent.PROCESS),
            KeywordIntentHandler(Intent.BANK_RECOMMENDATION),
        ),
        loan_calculator=AnnuityLoanCalculator(),
        knowledge_responder=RetrievalChatResponder(JsonKnowledgeRetriever()),
        state_store=InMemoryChatStateStore(),
    )


def get_async_session_factory():
    return _get_async_session_factory()
