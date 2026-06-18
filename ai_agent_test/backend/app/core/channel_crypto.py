"""Token encryption for messaging channel bot credentials."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.exceptions import BadRequestError


def _get_fernet() -> Fernet:
    """Build a Fernet instance from CHANNEL_ENCRYPTION_KEY.

    Fernet requires a 32-byte URL-safe base64-encoded key (44 chars).
    If the configured key is not already in that format, it is derived
    deterministically via SHA-256 so any arbitrary string is acceptable.
    """
    key = settings.CHANNEL_ENCRYPTION_KEY
    try:
        key_bytes = key.encode() if isinstance(key, str) else key
        # Fernet key must be exactly 44 URL-safe base64 chars (32 raw bytes)
        if len(key_bytes) != 44:
            raw = hashlib.sha256(key_bytes).digest()
            key_bytes = base64.urlsafe_b64encode(raw)
        return Fernet(key_bytes)
    except Exception as exc:
        raise BadRequestError(message="CHANNEL_ENCRYPTION_KEY is invalid") from exc


def encrypt_token(plain_token: str) -> str:
    """Encrypt a bot token for storage."""
    f = _get_fernet()
    return f.encrypt(plain_token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored bot token."""
    f = _get_fernet()
    try:
        return f.decrypt(encrypted_token.encode()).decode()
    except InvalidToken as exc:
        raise BadRequestError(
            message="Failed to decrypt bot token — check CHANNEL_ENCRYPTION_KEY"
        ) from exc
