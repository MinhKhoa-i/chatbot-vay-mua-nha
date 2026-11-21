from dataclasses import asdict
from decimal import Decimal

from app.domain.entities.conversation_memory import ConversationMemory
from app.infrastructure.security.payload_cipher import PayloadCipherError


MEMORY_SCHEMA_VERSION = 2
MEMORY_V1_KEYS = {
    "schema_version", "amount", "years", "user_provided_rate", "promo_rate",
    "promo_duration_months", "repayment_method", "verified_rate", "source_seq",
}
MEMORY_KEYS = MEMORY_V1_KEYS | {
    "property_value", "prepay_month", "grace_period_months", "base_rate",
    "assumed_floating_rate",
}
_DECIMAL_FIELDS = (
    "user_provided_rate", "promo_rate", "verified_rate", "base_rate", "assumed_floating_rate",
)


def encode_conversation_memory(memory: ConversationMemory) -> dict:
    payload = asdict(memory)
    payload["schema_version"] = MEMORY_SCHEMA_VERSION
    for name in _DECIMAL_FIELDS:
        if payload[name] is not None:
            payload[name] = str(payload[name])
    return payload


def decode_conversation_memory(profile: dict) -> ConversationMemory:
    payload = profile.get("conversation_memory")
    if payload is None:
        return ConversationMemory()
    try:
        if not isinstance(payload, dict):
            raise ValueError("Invalid conversation memory")
        schema_version = payload.get("schema_version")
        if schema_version == 1 and set(payload) == MEMORY_V1_KEYS:
            values = {**payload, **{name: None for name in MEMORY_KEYS - MEMORY_V1_KEYS}}
        elif schema_version == MEMORY_SCHEMA_VERSION and set(payload) == MEMORY_KEYS:
            values = dict(payload)
        else:
            raise ValueError("Unsupported conversation memory schema")
        values.pop("schema_version")
        for name in _DECIMAL_FIELDS:
            if values[name] is not None:
                if not isinstance(values[name], str):
                    raise ValueError(f"Invalid stored {name}")
                values[name] = Decimal(values[name])
        return ConversationMemory(**values)
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise PayloadCipherError("Invalid conversation memory") from exc
