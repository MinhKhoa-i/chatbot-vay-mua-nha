from dataclasses import asdict
from decimal import Decimal

from app.domain.entities.estimate_session import EstimateSession
from app.infrastructure.security.payload_cipher import PayloadCipherError


LEGACY_KEYS = {"amount", "years", "rate", "status"}
KEYS = LEGACY_KEYS | {"method", "promo_rate", "promo_duration_months"}


def encode_estimate_session(session: EstimateSession) -> dict:
    payload = asdict(session)
    for name in ("rate", "promo_rate"):
        if payload[name] is not None:
            payload[name] = str(payload[name])
    return payload


def decode_estimate_session(profile: dict) -> EstimateSession:
    payload = profile.get("estimate_session")
    if payload is None:
        return EstimateSession()
    try:
        # Phiên lưu trước khi có method/ưu đãi chỉ có 4 khóa cũ
        if not isinstance(payload, dict) or set(payload) not in (LEGACY_KEYS, KEYS):
            raise ValueError("Invalid estimate state")
        values = dict(payload)
        if set(payload) == LEGACY_KEYS:  # luồng cũ luôn là niên kim, lãi cố định cả kỳ
            values.update(method="annuity", promo_rate=None, promo_duration_months=0)
        for name in ("rate", "promo_rate"):
            if values.get(name) is not None:
                if not isinstance(values[name], str):
                    raise ValueError(f"Invalid stored {name}")
                values[name] = Decimal(values[name])
        return EstimateSession(**values)
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise PayloadCipherError("Invalid estimate state") from exc
