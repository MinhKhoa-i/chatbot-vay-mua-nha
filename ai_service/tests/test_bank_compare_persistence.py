import base64
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.entities.bank_compare_session import BankCompareSession
from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.chat_request import ChatRequest, ChatSnapshotUpdate
from app.domain.entities.estimate_session import EstimateSession
from app.infrastructure.db.bank_compare_state_codec import (
    decode_bank_compare_session,
    encode_bank_compare_session,
)
from app.infrastructure.db.conversation_repository import PostgresConversationRepository
from app.infrastructure.db.estimate_state_codec import encode_estimate_session
from app.infrastructure.security.payload_cipher import PayloadCipher, PayloadCipherError
from test_chat_checkpoint_commit import FakeSession


class ClaimSession(FakeSession):
    async def scalars(self, statement):
        return SimpleNamespace(all=lambda: [])


def test_bank_compare_state_codec_round_trips_every_field():
    state = BankCompareSession(
        amount=1_500_000_000,
        years=25,
        assumed_floating_rate=Decimal("9.75"),
        base_rate=Decimal("6.25"),
        method="reducing_balance",
        property_value=2_000_000_000,
        prepay_month=60,
        grace_period_months=12,
        status="collecting",
    )

    encoded = encode_bank_compare_session(state)

    assert encoded["assumed_floating_rate"] == "9.75"
    assert encoded["base_rate"] == "6.25"
    assert decode_bank_compare_session({"bank_compare_session": encoded}) == state


def test_bank_compare_state_codec_reads_completed_legacy_session_without_assumed_rate():
    old_state = {
        "amount": 1_000_000_000,
        "years": 20,
        "assumed_floating_rate": None,
        "base_rate": None,
        "method": "annuity",
        "method_explicit": False,
        "property_value": None,
        "prepay_month": None,
        "grace_period_months": 0,
        "status": "completed",
    }

    decoded = decode_bank_compare_session({"bank_compare_session": old_state})

    assert decoded.status == "completed"
    assert decoded.missing_fields == ("assumed_floating_rate",)


def test_bank_compare_state_codec_defaults_for_legacy_profile():
    assert decode_bank_compare_session({"slots": {}}) == BankCompareSession()


def test_bank_compare_state_codec_migrates_old_default_method_as_not_explicit():
    old_state = {
        "amount": 1_000_000_000,
        "years": 20,
        "assumed_floating_rate": None,
        "base_rate": None,
        "method": "annuity",
        "property_value": None,
        "prepay_month": None,
        "grace_period_months": 0,
        "status": "collecting",
    }

    decoded = decode_bank_compare_session({"bank_compare_session": old_state})

    assert decoded.method == "annuity"
    assert decoded.method_explicit is False


def test_bank_compare_state_codec_round_trips_explicit_method_marker():
    state = BankCompareSession(method="annuity", method_explicit=True)

    assert decode_bank_compare_session({
        "bank_compare_session": encode_bank_compare_session(state),
    }) == state


@pytest.mark.parametrize("payload", [
    [],
    {"amount": 100},
    {
        "amount": None, "years": None, "assumed_floating_rate": 1,
        "base_rate": None, "method": "annuity", "property_value": None,
        "prepay_month": None, "grace_period_months": 0, "status": "idle",
    },
])
def test_bank_compare_state_codec_rejects_malformed_profile(payload):
    with pytest.raises(PayloadCipherError):
        decode_bank_compare_session({"bank_compare_session": payload})


async def test_bank_compare_commit_encrypts_profile_and_next_claim_restores_state():
    cipher = PayloadCipher(base64.b64encode(b"k" * 32).decode("ascii"))
    conversation_id, request_id, token = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    checkpoint, profile = PostgresConversationRepository._initial_state()
    profile["slots"] = {"existing": {"value": "preserved", "status": "proposed"}}
    estimate_state = EstimateSession(amount=1_000_000_000, years=20, rate=Decimal("8.5"))
    profile["estimate_session"] = encode_estimate_session(estimate_state)
    profile_row = SimpleNamespace(
        revision=0,
        slots_ciphertext=cipher.encrypt_json(
            profile, table="conversation_profiles", column="slots_ciphertext", resource_id=conversation_id,
        ),
    )
    conversation = SimpleNamespace(
        id=conversation_id, status="active", version=0, active_request_id=request_id,
        expires_at=now + timedelta(days=1),
        checkpoint_ciphertext=cipher.encrypt_json(
            checkpoint, table="conversations", column="checkpoint_ciphertext", resource_id=conversation_id,
        ),
    )
    ledger = SimpleNamespace(
        id=request_id, status="processing", lease_token=token, snapshot_version=0,
        lease_expires_at=now + timedelta(seconds=90),
    )
    session = FakeSession([conversation, now, ledger, now, 0, profile_row])
    repository = PostgresConversationRepository(lambda: session, cipher)
    compare_state = BankCompareSession(
        amount=1_500_000_000,
        years=25,
        assumed_floating_rate=Decimal("9.75"),
        base_rate=Decimal("6.25"),
        method="reducing_balance",
        property_value=2_000_000_000,
        prepay_month=60,
        grace_period_months=12,
        status="collecting",
    )

    await repository.commit(
        ChatRequest(conversation_id, uuid4(), "So sánh khoản vay", 0),
        request_id=request_id,
        lease_token=token,
        snapshot_version=0,
        answer="Cần thêm thông tin.",
        state_update=ChatSnapshotUpdate(
            ChatIntent.BANK_COMPARE, bank_compare_session=compare_state,
        ),
    )

    saved_profile = cipher.decrypt_json(
        profile_row.slots_ciphertext,
        table="conversation_profiles",
        column="slots_ciphertext",
        resource_id=conversation_id,
    )
    saved_checkpoint = cipher.decrypt_json(
        conversation.checkpoint_ciphertext,
        table="conversations",
        column="checkpoint_ciphertext",
        resource_id=conversation_id,
    )
    assert decode_bank_compare_session(saved_profile) == compare_state
    assert saved_profile["slots"] == profile["slots"]
    assert saved_profile["estimate_session"] == profile["estimate_session"]
    assert saved_profile["profile_revision"] == profile_row.revision == saved_checkpoint["profile_revision"] == 1
    assert "bank_compare_session" not in saved_checkpoint
    assert ledger.status == "completed" and len(session.added) == 2

    conversation.expires_at = now + timedelta(days=30)
    claim_session = ClaimSession([conversation, now, None, profile_row])
    next_repository = PostgresConversationRepository(lambda: claim_session, cipher)
    claim = await next_repository.claim(
        ChatRequest(conversation_id, uuid4(), "Thời hạn vay", 1), "next-hash",
    )

    assert claim.kind == "claimed"
    assert claim.snapshot.bank_compare_session == compare_state
    assert claim.snapshot.estimate_session == estimate_state
    assert claim.snapshot.conversation_version == 1
