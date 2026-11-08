from dataclasses import asdict
from decimal import Decimal

from app.domain.entities.estimate_session import EstimateSession
from app.infrastructure.security.payload_cipher import PayloadCipherError


def encode_estimate_session(session: EstimateSession) -> dict:
    payload = asdict(session)
    if session.rate is not None:
        payload["rate"] = str(session.rate)
    return payload


def decode_estimate_session(profile: dict) -> EstimateSession:
    payload = profile.get("estimate_session")
    if payload is None:
        return EstimateSession()
    try:
        if not isinstance(payload, dict) or set(payload) != {"amount", "years", "rate", "status"}:
            raise ValueError("Invalid estimate state")
        values = dict(payload)
        if values["rate"] is not None:
            if not isinstance(values["rate"], str):
                raise ValueError("Invalid stored rate")
            values["rate"] = Decimal(values["rate"])
        return EstimateSession(**values)
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise PayloadCipherError("Invalid estimate state") from exc
