import base64
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.chat_request import ChatRequest, ChatSnapshotUpdate
from app.domain.entities.estimate_session import EstimateSession
from app.infrastructure.db.conversation_repository import PostgresConversationRepository
from app.infrastructure.db.estimate_state_codec import decode_estimate_session
from app.infrastructure.security.payload_cipher import PayloadCipher
from test_chat_checkpoint_commit import FakeSession


class ClaimSession(FakeSession):
    async def scalars(self, statement):
        return SimpleNamespace(all=lambda: [])


async def test_estimate_commit_encrypts_profile_and_next_claim_restores_state():
    cipher = PayloadCipher(base64.b64encode(b"k" * 32).decode("ascii"))
    conversation_id, request_id, token = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    checkpoint, profile = PostgresConversationRepository._initial_state()
    profile["slots"] = {"existing": {"value": "preserved", "status": "proposed"}}
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
    state = EstimateSession(1_000_000_000, 20, Decimal("8.5"), "awaiting_confirmation")
    session = FakeSession([conversation, now, ledger, now, 0, profile_row])
    repository = PostgresConversationRepository(lambda: session, cipher)
    await repository.commit(
        ChatRequest(conversation_id, uuid4(), "20 năm, 8,5%", 0), request_id=request_id,
        lease_token=token, snapshot_version=0, answer="Vui lòng xác nhận",
        state_update=ChatSnapshotUpdate(ChatIntent.ESTIMATE, state),
    )
    saved_profile = cipher.decrypt_json(
        profile_row.slots_ciphertext, table="conversation_profiles", column="slots_ciphertext",
        resource_id=conversation_id,
    )
    saved_checkpoint = cipher.decrypt_json(
        conversation.checkpoint_ciphertext, table="conversations", column="checkpoint_ciphertext",
        resource_id=conversation_id,
    )
    assert decode_estimate_session(saved_profile) == state
    assert saved_profile["slots"] == profile["slots"]
    assert saved_profile["profile_revision"] == profile_row.revision == saved_checkpoint["profile_revision"] == 1
    assert "estimate_session" not in saved_checkpoint
    assert ledger.status == "completed" and len(session.added) == 2

    # A real database evaluates the expiration expression assigned during commit.
    conversation.expires_at = now + timedelta(days=30)
    claim_session = ClaimSession([conversation, now, None, profile_row])
    next_repository = PostgresConversationRepository(lambda: claim_session, cipher)
    claim = await next_repository.claim(ChatRequest(conversation_id, uuid4(), "Xác nhận tính", 1), "next-hash")
    assert claim.kind == "claimed"
    assert claim.snapshot.estimate_session == state
    assert claim.snapshot.conversation_version == 1
