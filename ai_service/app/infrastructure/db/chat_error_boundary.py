import logging
from functools import wraps

from sqlalchemy.exc import SQLAlchemyError

from app.domain.errors import ConversationStateError
from app.infrastructure.security.payload_cipher import PayloadCipherError


logger = logging.getLogger(__name__)


def chat_repository_errors(operation: str):
    """Translate storage failures at the repository boundary, retaining their cause."""
    def decorate(method):
        @wraps(method)
        async def wrapped(*args, **kwargs):
            try:
                return await method(*args, **kwargs)
            except PayloadCipherError as exc:
                logger.exception("Conversation state integrity failure (operation=%s)", operation)
                raise ConversationStateError(stage=operation, corrupt=True) from exc
            except SQLAlchemyError as exc:
                logger.exception("Conversation database failure (operation=%s)", operation)
                raise ConversationStateError(stage=operation) from exc
            except Exception:
                logger.exception("Conversation repository failure (operation=%s)", operation)
                raise
        return wrapped
    return decorate
