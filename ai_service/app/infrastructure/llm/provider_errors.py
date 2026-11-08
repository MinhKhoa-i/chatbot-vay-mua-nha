from openai import APIError, APIStatusError, APITimeoutError

from app.domain.ports.chat_completion import ChatProviderUnavailable


def translate_provider_error(error: APIError) -> ChatProviderUnavailable:
    """Keep provider failure semantics identical for generation and classification."""
    if isinstance(error, APITimeoutError):
        return ChatProviderUnavailable(code="MODEL_TIMEOUT")
    if isinstance(error, APIStatusError):
        if error.status_code in {401, 403}:
            return ChatProviderUnavailable(code="MODEL_AUTHENTICATION_FAILED", retryable=False)
        if error.status_code == 429:
            return ChatProviderUnavailable(code="MODEL_RATE_LIMITED")
        if error.status_code < 500:
            return ChatProviderUnavailable(code="MODEL_REQUEST_REJECTED", retryable=False)
    return ChatProviderUnavailable()
