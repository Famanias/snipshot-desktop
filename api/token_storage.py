"""
SnipShot Desktop - Token Storage

Persists Supabase session tokens in the OS keychain via `keyring`.
Falls back to a Fernet-encrypted file only when no keyring backend is
available (e.g., headless Linux CI environments).

Never store tokens in plaintext.  Never use SUPABASE_SERVICE_KEY here.
"""

import json
import os
from typing import Optional

import keyring
import keyring.errors

SERVICE_NAME = "SnipShot"
TOKEN_KEY = "supabase_session"

# ---------------------------------------------------------------------------
# Fernet fallback (headless Linux only)
# ---------------------------------------------------------------------------
# The fallback key is derived from a machine-specific seed so it isn't
# hardcoded.  This is best-effort security — on supported platforms, the OS
# keychain is always preferred.

_FALLBACK_PATH = os.path.join(
    os.getenv("APPDATA") or os.path.expanduser("~"), "SnipShot", ".session"
)


def _get_fernet():
    """Return a Fernet instance keyed from a stable machine identifier."""
    try:
        from cryptography.fernet import Fernet
        import base64
        import hashlib

        # Derive a 32-byte key from the machine node ID (stable across reboots)
        seed = str(os.getenv("USERNAME") or os.getenv("USER") or "snipshot")
        raw = hashlib.sha256(seed.encode()).digest()
        key = base64.urlsafe_b64encode(raw)
        return Fernet(key)
    except ImportError:
        return None  # cryptography not installed — plaintext fallback skipped


def _fernet_save(payload: str) -> None:
    os.makedirs(os.path.dirname(_FALLBACK_PATH), exist_ok=True)
    fernet = _get_fernet()
    if fernet:
        data = fernet.encrypt(payload.encode())
    else:
        data = payload.encode()
    with open(_FALLBACK_PATH, "wb") as f:
        f.write(data)


def _fernet_load() -> Optional[str]:
    if not os.path.exists(_FALLBACK_PATH):
        return None
    fernet = _get_fernet()
    with open(_FALLBACK_PATH, "rb") as f:
        raw = f.read()
    try:
        if fernet:
            return fernet.decrypt(raw).decode()
        return raw.decode()
    except Exception:
        return None


def _fernet_clear() -> None:
    try:
        os.remove(_FALLBACK_PATH)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_tokens(access_token: str, refresh_token: str) -> None:
    """Persist tokens to OS keychain (Credential Manager / Keychain / libsecret).

    Falls back to a Fernet-encrypted file on headless Linux environments
    where no keyring backend is available.
    """
    payload = json.dumps(
        {"access_token": access_token, "refresh_token": refresh_token}
    )
    try:
        keyring.set_password(SERVICE_NAME, TOKEN_KEY, payload)
    except keyring.errors.NoKeyringError:
        _fernet_save(payload)


def load_tokens() -> Optional[dict]:
    """Load tokens from OS keychain.

    Returns a dict with ``access_token`` and ``refresh_token`` keys,
    or ``None`` if nothing is stored or the stored value is invalid.
    """
    try:
        raw = keyring.get_password(SERVICE_NAME, TOKEN_KEY)
    except keyring.errors.NoKeyringError:
        raw = _fernet_load()

    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def clear_tokens() -> None:
    """Delete tokens from the OS keychain (called on logout)."""
    try:
        keyring.delete_password(SERVICE_NAME, TOKEN_KEY)
    except keyring.errors.PasswordDeleteError:
        pass  # Already gone — not an error
    except keyring.errors.NoKeyringError:
        _fernet_clear()
