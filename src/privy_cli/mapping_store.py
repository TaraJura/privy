from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ModuleNotFoundError as exc:  # pragma: no cover - runtime guard
    Fernet = None  # type: ignore[assignment]
    InvalidToken = Exception  # type: ignore[assignment]
    hashes = None  # type: ignore[assignment]
    PBKDF2HMAC = None  # type: ignore[assignment]
    _CRYPTO_IMPORT_ERROR = exc
else:
    _CRYPTO_IMPORT_ERROR = None

PBKDF2_ITERATIONS = 390_000
SALT_BYTES = 16


class MappingStoreError(RuntimeError):
    pass


@dataclass
class MappingData:
    placeholders: dict[str, dict[str, str]]
    created_at: str

    @classmethod
    def create_empty(cls) -> "MappingData":
        return cls(
            placeholders={},
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "created_at": self.created_at,
            "placeholders": self.placeholders,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MappingData":
        placeholders = value.get("placeholders", {})
        if not isinstance(placeholders, dict):
            raise MappingStoreError("Invalid mapping payload: placeholders must be an object.")
        created_at = str(value.get("created_at", ""))
        return cls(placeholders=placeholders, created_at=created_at)


def _derive_fernet_key(password: str, salt: bytes, iterations: int) -> bytes:
    _ensure_crypto_available()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    raw_key = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw_key)


def write_encrypted_mapping(path: Path, mapping: MappingData, password: str) -> None:
    _ensure_crypto_available()
    salt = os.urandom(SALT_BYTES)
    key = _derive_fernet_key(password=password, salt=salt, iterations=PBKDF2_ITERATIONS)
    fernet = Fernet(key)
    plaintext = json.dumps(mapping.to_dict(), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ciphertext = fernet.encrypt(plaintext)
    payload = {
        "version": 1,
        "kdf": "pbkdf2-sha256",
        "iterations": PBKDF2_ITERATIONS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def read_encrypted_mapping(path: Path, password: str) -> MappingData:
    _ensure_crypto_available()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MappingStoreError(f"Mapping file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MappingStoreError(f"Mapping file is not valid JSON: {path}") from exc

    try:
        salt = base64.b64decode(payload["salt"])
        ciphertext = base64.b64decode(payload["ciphertext"])
        iterations = int(payload.get("iterations", PBKDF2_ITERATIONS))
    except (KeyError, ValueError, TypeError) as exc:
        raise MappingStoreError("Mapping file payload is missing required encryption metadata.") from exc

    key = _derive_fernet_key(password=password, salt=salt, iterations=iterations)
    fernet = Fernet(key)

    try:
        plaintext = fernet.decrypt(ciphertext)
    except InvalidToken as exc:
        raise MappingStoreError("Failed to decrypt mapping. Password may be incorrect.") from exc

    try:
        mapping_obj = json.loads(plaintext.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise MappingStoreError("Decrypted mapping payload is invalid JSON.") from exc

    return MappingData.from_dict(mapping_obj)


def _ensure_crypto_available() -> None:
    if _CRYPTO_IMPORT_ERROR is not None:
        raise MappingStoreError(
            "Missing dependency 'cryptography'. Install project dependencies first, e.g. "
            "'pip install -e .'."
        ) from _CRYPTO_IMPORT_ERROR
