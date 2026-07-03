"""
Phase 2 — Session Tokens
Generates and validates session-scoped tokens for MCP tool calls.
Each token is tied to a conversation ID, customer ID, and expiry time.
Phase 5 will replace this with full JWT signing — for now we use
a signed HMAC token that is verifiable without a database lookup.
"""

import hmac
import hashlib
import time
import json
import os
import base64

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY       = os.getenv("SESSION_SECRET", "dev_secret_changeme_in_production")
TOKEN_TTL_SECS   = 3600   # 1 hour


# ── Token creation ────────────────────────────────────────────────────────────
def create_session_token(conversation_id: str, customer_id: str, profile: str) -> dict:
    """
    Create a signed session token for a conversation.

    Returns:
    {
        "token":           str,   # Bearer token to pass to MCP servers
        "conversation_id": str,
        "customer_id":     str,
        "profile":         str,
        "expires_at":      float, # unix timestamp
    }
    """
    issued_at  = time.time()
    expires_at = issued_at + TOKEN_TTL_SECS

    payload = {
        "conversation_id": conversation_id,
        "customer_id":     customer_id,
        "profile":         profile,
        "issued_at":       issued_at,
        "expires_at":      expires_at,
    }

    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode()

    signature = hmac.new(
        SECRET_KEY.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()

    token = f"session_{payload_b64}.{signature}"

    return {
        "token":           token,
        "conversation_id": conversation_id,
        "customer_id":     customer_id,
        "profile":         profile,
        "expires_at":      expires_at,
    }


# ── Token validation ──────────────────────────────────────────────────────────
def validate_session_token(token: str) -> dict:
    """
    Validate a session token.

    Returns:
    {
        "valid":           bool,
        "reason":          str,
        "conversation_id": str | None,
        "customer_id":     str | None,
        "profile":         str | None,
        "expires_at":      float | None,
    }
    """
    try:
        if not token.startswith("session_"):
            return _invalid("Token does not start with 'session_'")

        # Strip "session_" prefix then split payload and signature
        raw         = token[len("session_"):]
        parts       = raw.rsplit(".", 1)
        if len(parts) != 2:
            return _invalid("Malformed token structure")

        payload_b64, signature = parts

        # Verify signature
        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return _invalid("Invalid token signature")

        # Decode payload
        payload = json.loads(
            base64.urlsafe_b64decode(payload_b64.encode()).decode()
        )

        # Check expiry
        if time.time() > payload["expires_at"]:
            return _invalid("Token has expired")

        return {
            "valid":           True,
            "reason":          "ok",
            "conversation_id": payload["conversation_id"],
            "customer_id":     payload["customer_id"],
            "profile":         payload["profile"],
            "expires_at":      payload["expires_at"],
        }

    except Exception as e:
        return _invalid(f"Token validation error: {e}")


def _invalid(reason: str) -> dict:
    return {
        "valid":           False,
        "reason":          reason,
        "conversation_id": None,
        "customer_id":     None,
        "profile":         None,
        "expires_at":      None,
    }


# ── In-memory token store ─────────────────────────────────────────────────────
# Phase 5 moves this to Postgres/Redis
_active_tokens: dict[str, dict] = {}


def issue_token(conversation_id: str, customer_id: str, profile: str) -> str:
    """Issue and store a new session token. Returns the token string."""
    token_data = create_session_token(conversation_id, customer_id, profile)
    _active_tokens[conversation_id] = token_data
    return token_data["token"]


def get_token(conversation_id: str) -> str | None:
    """Get the active token for a conversation."""
    data = _active_tokens.get(conversation_id)
    if not data:
        return None
    # Re-validate before returning
    result = validate_session_token(data["token"])
    if not result["valid"]:
        _active_tokens.pop(conversation_id, None)
        return None
    return data["token"]


def revoke_token(conversation_id: str):
    """Revoke token when conversation ends."""
    _active_tokens.pop(conversation_id, None)
