"""
Supabase Authentication utilities

Handles both:
1. Supabase Auth JWT verification
2. Custom JWT for additional flexibility
"""

import os
from functools import lru_cache
from typing import Optional
import jwt
from jwt import PyJWKClient
from dotenv import load_dotenv

load_dotenv()

# Supabase JWT settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
HS256_ALGORITHM = "HS256"
ASYMMETRIC_ALGORITHMS = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}


@lru_cache()
def _get_jwks_client() -> Optional[PyJWKClient]:
    """Create a cached JWKS client for Supabase asymmetric JWT verification."""
    if not SUPABASE_URL:
        return None

    jwks_url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url)


def _decode_hs256_token(token: str) -> Optional[dict]:
    """Verify legacy HS256 tokens using SUPABASE_JWT_SECRET."""
    if not SUPABASE_JWT_SECRET:
        return None

    try:
        return jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[HS256_ALGORITHM],
            options={"verify_aud": False},
        )
    except jwt.InvalidTokenError:
        return None


def _decode_asymmetric_token(token: str, algorithm: str) -> Optional[dict]:
    """Verify RS/ES tokens using Supabase JWKS."""
    if algorithm not in ASYMMETRIC_ALGORITHMS:
        return None

    jwks_client = _get_jwks_client()
    if jwks_client is None:
        return None

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            options={"verify_aud": False},
        )
    except Exception:
        return None


def decode_supabase_token(token: str) -> Optional[dict]:
    """
    Decode and verify a Supabase access token.
    Returns the payload if valid, None otherwise.
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError:
        return None

    algorithm = header.get("alg")

    if algorithm == HS256_ALGORITHM:
        payload = _decode_hs256_token(token)
        if payload is not None:
            return payload
    elif algorithm:
        payload = _decode_asymmetric_token(token, algorithm)
        if payload is not None:
            return payload

    # Compatibility fallback when token header is missing/invalid for expected setup
    payload = _decode_hs256_token(token)
    if payload is not None:
        return payload

    if algorithm:
        return _decode_asymmetric_token(token, algorithm)

    return None


def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract user ID from Supabase token"""
    payload = decode_supabase_token(token)
    if payload:
        return payload.get("sub")  # Supabase uses 'sub' for user ID
    return None

