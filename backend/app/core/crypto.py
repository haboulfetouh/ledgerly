"""Symmetric encryption for tenant-supplied secrets (ERP credentials, etc.)
at rest — PRD backlog LED-030. Not a substitute for a real secrets vault at
enterprise scale, but the right MVP-scoped control for a self-hosted stack.
"""

from __future__ import annotations

import json

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _fernet() -> Fernet:
    key = get_settings().secrets_encryption_key
    if not key:
        raise RuntimeError("SECRETS_ENCRYPTION_KEY is not configured")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_json(data: dict) -> str:
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_json(token: str) -> dict:
    return json.loads(_fernet().decrypt(token.encode()).decode())
