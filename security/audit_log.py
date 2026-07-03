"""
Phase 2 — Audit Logging
Append-only audit_log table in Postgres.
Every MCP tool call, PII detection event, and scope violation is logged.
No records are ever updated or deleted — append only.
"""

import os
import json
import time
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql://pocketwallet:localdev@localhost:5432/pocketwallet"
)

# ── Event types ───────────────────────────────────────────────────────────────
EVENT_TOOL_CALL      = "tool_call"
EVENT_TOOL_BLOCKED   = "tool_blocked"
EVENT_PII_DETECTED   = "pii_detected"
EVENT_SCOPE_VIOLATION= "scope_violation"
EVENT_SESSION_ISSUED = "session_issued"
EVENT_SESSION_REVOKED= "session_revoked"


# ── DB setup ──────────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_audit_table():
    """
    Create the audit_log table if it does not exist.
    Called once at startup.
    """
    sql = """
    CREATE TABLE IF NOT EXISTS audit_log (
        id               BIGSERIAL PRIMARY KEY,
        event_type       TEXT        NOT NULL,
        conversation_id  TEXT,
        customer_id      TEXT,
        tool_name        TEXT,
        server_name      TEXT,
        profile          TEXT,
        pii_types        JSONB,
        details          JSONB,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- Index for common query patterns
    CREATE INDEX IF NOT EXISTS idx_audit_customer
        ON audit_log (customer_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_audit_conversation
        ON audit_log (conversation_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_audit_event_type
        ON audit_log (event_type, created_at DESC);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print("audit_log table ready")


# ── Logging functions ─────────────────────────────────────────────────────────
def _write_log(
    event_type:      str,
    conversation_id: str  = None,
    customer_id:     str  = None,
    tool_name:       str  = None,
    server_name:     str  = None,
    profile:         str  = None,
    pii_types:       list = None,
    details:         dict = None,
):
    sql = """
    INSERT INTO audit_log
        (event_type, conversation_id, customer_id, tool_name,
         server_name, profile, pii_types, details)
    VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    event_type,
                    conversation_id,
                    customer_id,
                    tool_name,
                    server_name,
                    profile,
                    json.dumps(pii_types or []),
                    json.dumps(details   or {}),
                ))
            conn.commit()
    except Exception as e:
        # Never let audit logging crash the main flow
        print(f"[AUDIT ERROR] Failed to write log: {e}")


def log_tool_call(
    conversation_id: str,
    customer_id:     str,
    tool_name:       str,
    server_name:     str,
    profile:         str,
    result_summary:  str = "",
):
    _write_log(
        event_type      = EVENT_TOOL_CALL,
        conversation_id = conversation_id,
        customer_id     = customer_id,
        tool_name       = tool_name,
        server_name     = server_name,
        profile         = profile,
        details         = {"result_summary": result_summary},
    )


def log_tool_blocked(
    conversation_id: str,
    customer_id:     str,
    tool_name:       str,
    server_name:     str,
    profile:         str,
    reason:          str,
):
    _write_log(
        event_type      = EVENT_TOOL_BLOCKED,
        conversation_id = conversation_id,
        customer_id     = customer_id,
        tool_name       = tool_name,
        server_name     = server_name,
        profile         = profile,
        details         = {"reason": reason},
    )


def log_pii_detected(
    conversation_id: str,
    customer_id:     str,
    pii_types:       list,
    pii_count:       int,
):
    _write_log(
        event_type      = EVENT_PII_DETECTED,
        conversation_id = conversation_id,
        customer_id     = customer_id,
        pii_types       = pii_types,
        details         = {"pii_count": pii_count},
    )


def log_session_issued(
    conversation_id: str,
    customer_id:     str,
    profile:         str,
    expires_at:      float,
):
    _write_log(
        event_type      = EVENT_SESSION_ISSUED,
        conversation_id = conversation_id,
        customer_id     = customer_id,
        profile         = profile,
        details         = {
            "expires_at": datetime.fromtimestamp(
                expires_at, tz=timezone.utc
            ).isoformat()
        },
    )


def log_session_revoked(conversation_id: str, customer_id: str):
    _write_log(
        event_type      = EVENT_SESSION_REVOKED,
        conversation_id = conversation_id,
        customer_id     = customer_id,
    )


# ── Query helpers ─────────────────────────────────────────────────────────────
def get_logs_for_conversation(conversation_id: str) -> list:
    """Pull all audit events for a conversation (newest first)."""
    sql = """
    SELECT id, event_type, customer_id, tool_name, server_name,
           profile, pii_types, details, created_at
    FROM   audit_log
    WHERE  conversation_id = %s
    ORDER  BY created_at DESC
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (conversation_id,))
            return [dict(row) for row in cur.fetchall()]


def get_logs_for_customer(customer_id: str, limit: int = 50) -> list:
    """Pull recent audit events for a customer."""
    sql = """
    SELECT id, event_type, conversation_id, tool_name, server_name,
           profile, pii_types, details, created_at
    FROM   audit_log
    WHERE  customer_id = %s
    ORDER  BY created_at DESC
    LIMIT  %s
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (customer_id, limit))
            return [dict(row) for row in cur.fetchall()]
