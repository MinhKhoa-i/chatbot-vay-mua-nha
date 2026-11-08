import base64
from uuid import uuid4

import pytest

from app.infrastructure.db.models import (
    ConversationMessageModel,
    ConversationModel,
    ConversationProfileModel,
    MessageRequestModel,
)
from app.infrastructure.security.payload_cipher import PayloadCipher, PayloadCipherError


def test_payload_cipher_round_trip_and_resource_binding():
    cipher = PayloadCipher(base64.b64encode(b"k" * 32).decode("ascii"))
    conversation_id = uuid4()
    envelope = cipher.encrypt_json(
        {"schema_version": 1, "text": "Tôi muốn vay 2 tỷ"},
        table="conversations",
        column="checkpoint_ciphertext",
        resource_id=conversation_id,
    )
    assert "2 tỷ".encode("utf-8") not in envelope
    assert cipher.decrypt_json(
        envelope,
        table="conversations",
        column="checkpoint_ciphertext",
        resource_id=conversation_id,
    ) == {"schema_version": 1, "text": "Tôi muốn vay 2 tỷ"}
    with pytest.raises(PayloadCipherError):
        cipher.decrypt_json(
            envelope,
            table="messages",
            column="content_ciphertext",
            resource_id=conversation_id,
        )


def test_payload_cipher_rejects_bad_key_and_tampered_envelope():
    with pytest.raises(PayloadCipherError):
        PayloadCipher("not-base64")
    cipher = PayloadCipher(base64.b64encode(b"k" * 32).decode("ascii"))
    conversation_id = uuid4()
    envelope = bytearray(cipher.encrypt_json(
        {"content": "sensitive"},
        table="messages",
        column="content_ciphertext",
        resource_id=conversation_id,
    ))
    envelope[-1] ^= 1
    with pytest.raises(PayloadCipherError):
        cipher.decrypt_json(
            bytes(envelope),
            table="messages",
            column="content_ciphertext",
            resource_id=conversation_id,
        )


def test_conversation_tables_use_ciphertext_for_private_fields_and_expected_keys():
    assert ConversationModel.__table__.c.checkpoint_ciphertext.type.__class__.__name__ == "LargeBinary"
    assert ConversationProfileModel.__table__.c.slots_ciphertext.type.__class__.__name__ == "LargeBinary"
    assert ConversationMessageModel.__table__.c.content_ciphertext.type.__class__.__name__ == "LargeBinary"
    assert MessageRequestModel.__table__.c.response_ciphertext.type.__class__.__name__ == "LargeBinary"
    assert any(
        constraint.__class__.__name__ == "UniqueConstraint"
        and set(constraint.columns.keys()) == {"conversation_id", "seq"}
        for constraint in ConversationMessageModel.__table__.constraints
    )
