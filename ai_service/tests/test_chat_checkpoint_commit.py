import base64
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.chat_request import ChatRequest, ChatSnapshotUpdate
from app.domain.entities.loan_estimate import LoanEstimateInput, LoanEstimateResult
from app.domain.errors import ConversationStateError
from app.infrastructure.db.conversation_repository import PostgresConversationRepository
from app.infrastructure.security.payload_cipher import PayloadCipher, PayloadCipherError


class FakeSession:
    def __init__(self, values):
        self.values = iter(values)
        self.added = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def begin(self):
        return self

    async def scalar(self, statement):
        return next(self.values)

    def add(self, row):
        self.added.append(row)


@pytest.mark.parametrize("legacy, corrupt", [(False, False), (True, False), (True, True)])
async def test_commit_records_one_intent_without_modifying_profile(legacy, corrupt):
    cipher = PayloadCipher(base64.b64encode(b"k" * 32).decode("ascii"))
    conversation_id, request_id, token = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    checkpoint, profile = PostgresConversationRepository._initial_state()
    if legacy:
        checkpoint.update(
            current_stage="COLLECTING",
            pending_tasks=[{"kind": "calculation", "required_slots": ["loan_term_months"]}],
            pending_question={"kind": "slot", "field": "loan_term_months"},
            profile_revision=2,
        )
        profile.update(
            profile_revision=2,
            slots={"loan_amount_vnd": {"value": 2_000_000_000, "status": "proposed"}},
            confirmed_revision=2,
            confirmed_snapshot_hash="legacy-hash",
        )
    if corrupt:
        checkpoint["profile_revision"] += 1
    profile_blob = cipher.encrypt_json(
        profile, table="conversation_profiles", column="slots_ciphertext", resource_id=conversation_id,
    )
    profile_row = SimpleNamespace(revision=profile["profile_revision"], slots_ciphertext=profile_blob)
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
    if corrupt:
        with pytest.raises(ConversationStateError, match="STATE_CORRUPTED") as caught:
            await repository.commit(
                ChatRequest(conversation_id, uuid4(), "Hồ sơ vay?", 0), request_id=request_id,
                lease_token=token, snapshot_version=0, answer="Theo tài liệu...",
                state_update=ChatSnapshotUpdate(ChatIntent.RETRIEVAL),
            )
        assert isinstance(caught.value.__cause__, PayloadCipherError)
        assert caught.value.stage == "commit"
        assert conversation.version == 0
        assert ledger.status == "processing"
        return
    result = await repository.commit(
        ChatRequest(conversation_id, uuid4(), "Hồ sơ vay?", 0),
        request_id=request_id, lease_token=token, snapshot_version=0, answer="Theo tài liệu...",
        state_update=ChatSnapshotUpdate(ChatIntent.RETRIEVAL),
    )
    saved = cipher.decrypt_json(
        conversation.checkpoint_ciphertext, table="conversations", column="checkpoint_ciphertext",
        resource_id=conversation_id,
    )
    assert result.response_status == 200
    assert result.response_body["estimate"] is None
    assert result.version == conversation.version == saved["conversation_version"] == 1
    assert saved["active_intents"] == ["retrieval"]
    assert saved["pending_tasks"] == [] and saved["pending_question"] is None
    assert saved["profile_revision"] == profile_row.revision == profile["profile_revision"]
    assert profile_row.slots_ciphertext == profile_blob
    assert len(session.added) == 2
    assert ledger.status == "completed"
    assert conversation.active_request_id is None


def test_estimate_serialization_preserves_decimal_rate_as_string():
    result = LoanEstimateResult(
        LoanEstimateInput(1_000_000_000, 20, Decimal("9.5")),
        8_770_000,
        1_104_800_000,
        "2026-10-31",
    )

    assert PostgresConversationRepository._serialize_estimate(result) == {
        "input": {"amount": 1_000_000_000, "years": 20, "rate": "9.5"},
        "monthly_payment": 8_770_000,
        "total_interest": 1_104_800_000,
        "updated_at": "2026-10-31",
    }
    assert PostgresConversationRepository._serialize_estimate(None) is None
