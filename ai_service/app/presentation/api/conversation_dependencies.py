from functools import lru_cache

from fastapi import HTTPException

from app.application.use_cases.conversation_management import ConversationManagement
from app.core.config import get_settings
from app.infrastructure.db.conversation_repository import PostgresConversationRepository
from app.infrastructure.db.session import get_async_session_factory
from app.infrastructure.security.payload_cipher import PayloadCipher, PayloadCipherError


@lru_cache
def _get_cipher() -> PayloadCipher:
    settings = get_settings()
    if not settings.data_encryption_key_base64:
        raise PayloadCipherError("conversation encryption key is not configured")
    return PayloadCipher(settings.data_encryption_key_base64)


def get_conversation_management() -> ConversationManagement:
    try:
        return ConversationManagement(
            PostgresConversationRepository(get_async_session_factory(), _get_cipher())
        )
    except (RuntimeError, PayloadCipherError) as exc:
        raise HTTPException(status_code=503, detail="STATE_UNAVAILABLE") from exc
