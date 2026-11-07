import hashlib
import json
import unicodedata
from uuid import UUID


def chat_request_fingerprint(conversation_id: UUID, text: str, expected_version: int | None) -> str:
    canonical = {
        "operation": "send_message",
        "conversation_id": str(conversation_id),
        "body": {
            "expected_version": expected_version,
            "text": unicodedata.normalize("NFC", text),
        },
    }
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
