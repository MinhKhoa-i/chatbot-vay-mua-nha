import base64
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.infrastructure.db.conversation_repository import PostgresConversationRepository
from app.infrastructure.db.models import ConversationProfileModel
from app.infrastructure.security.payload_cipher import PayloadCipher


class FakeSession:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id
        self.added = []
        self.flushed = False
        self.statement = None

    async def scalar(self, statement):
        self.statement = statement
        return self.inserted_id

    def add(self, instance):
        self.added.append(instance)

    async def flush(self):
        self.flushed = True


@pytest.mark.parametrize("conversation_exists", [True, False])
async def test_insert_conversation_if_absent_does_not_replace_existing(conversation_exists):
    conversation_id = uuid4()
    session = FakeSession(None if conversation_exists else conversation_id)
    repository = PostgresConversationRepository(None, PayloadCipher(base64.b64encode(b"k" * 32).decode("ascii")))

    created = await repository._insert_conversation_if_absent(session, conversation_id)

    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (id) DO NOTHING" in sql
    assert "RETURNING conversations.id" in sql
    assert created is not conversation_exists
    if conversation_exists:
        assert session.added == []
        assert not session.flushed
    else:
        assert len(session.added) == 1
        assert isinstance(session.added[0], ConversationProfileModel)
        assert session.added[0].conversation_id == conversation_id
        assert session.flushed
        assert session.statement.compile().params["checkpoint_ciphertext"]


def test_initial_state_has_empty_profile_and_new_checkpoint():
    checkpoint, profile = PostgresConversationRepository._initial_state()

    assert checkpoint["conversation_version"] == 0
    assert checkpoint["current_stage"] == "NEW"
    assert profile["profile_revision"] == 0
    assert profile["slots"] == {}
