import base64
import binascii
import json
import secrets
from typing import Any
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class PayloadCipherError(RuntimeError):
    """Raised when encrypted state cannot be safely read or written."""


class PayloadCipher:
    """AES-256-GCM payload envelope with resource-bound additional data."""

    _SCHEMA_VERSION = 1
    _KEY_VERSION = 1
    _NONCE_BYTES = 12

    def __init__(self, key_base64: str) -> None:
        try:
            key = base64.b64decode(key_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise PayloadCipherError("DATA_ENCRYPTION_KEY_BASE64 must be valid base64") from exc
        if len(key) != 32:
            raise PayloadCipherError("DATA_ENCRYPTION_KEY_BASE64 must decode to exactly 32 bytes")
        self._cipher = AESGCM(key)

    @staticmethod
    def _aad(table: str, column: str, resource_id: UUID, schema_version: int) -> bytes:
        return f"{table}:{column}:{resource_id}:{schema_version}".encode("utf-8")

    def encrypt_json(self, value: dict[str, Any], *, table: str, column: str, resource_id: UUID) -> bytes:
        try:
            plaintext = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
            nonce = secrets.token_bytes(self._NONCE_BYTES)
            aad = self._aad(table, column, resource_id, self._SCHEMA_VERSION)
            ciphertext = self._cipher.encrypt(nonce, plaintext, aad)
            return bytes([self._KEY_VERSION, self._SCHEMA_VERSION]) + nonce + ciphertext
        except (TypeError, ValueError) as exc:
            raise PayloadCipherError("payload could not be serialized") from exc

    def decrypt_json(self, envelope: bytes, *, table: str, column: str, resource_id: UUID) -> dict[str, Any]:
        if len(envelope) < 2 + self._NONCE_BYTES + 16:
            raise PayloadCipherError("encrypted payload envelope is malformed")
        key_version, schema_version = envelope[0], envelope[1]
        if key_version != self._KEY_VERSION or schema_version != self._SCHEMA_VERSION:
            raise PayloadCipherError("encrypted payload version is unsupported")
        nonce = envelope[2 : 2 + self._NONCE_BYTES]
        ciphertext = envelope[2 + self._NONCE_BYTES :]
        aad = self._aad(table, column, resource_id, schema_version)
        try:
            decoded = json.loads(self._cipher.decrypt(nonce, ciphertext, aad))
        except (InvalidTag, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PayloadCipherError("encrypted payload authentication failed") from exc
        if not isinstance(decoded, dict):
            raise PayloadCipherError("encrypted payload must decode to an object")
        return decoded
