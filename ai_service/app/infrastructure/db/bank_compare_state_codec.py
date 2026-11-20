from dataclasses import asdict
from decimal import Decimal

from app.domain.entities.bank_compare_session import BankCompareSession
from app.infrastructure.security.payload_cipher import PayloadCipherError


BANK_COMPARE_KEYS = {
    "amount", "years", "assumed_floating_rate", "base_rate", "method", "property_value",
    "prepay_month", "grace_period_months", "status",
}


def encode_bank_compare_session(session: BankCompareSession) -> dict:
    payload = asdict(session)
    for name in ("assumed_floating_rate", "base_rate"):
        if payload[name] is not None:
            payload[name] = str(payload[name])
    return payload


def decode_bank_compare_session(profile: dict) -> BankCompareSession:
    payload = profile.get("bank_compare_session")
    if payload is None:
        return BankCompareSession()
    try:
        if not isinstance(payload, dict) or set(payload) != BANK_COMPARE_KEYS:
            raise ValueError("Invalid bank comparison state")
        values = dict(payload)
        for name in ("assumed_floating_rate", "base_rate"):
            if values[name] is not None:
                if not isinstance(values[name], str):
                    raise ValueError(f"Invalid stored {name}")
                values[name] = Decimal(values[name])
        return BankCompareSession(**values)
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise PayloadCipherError("Invalid bank comparison state") from exc
