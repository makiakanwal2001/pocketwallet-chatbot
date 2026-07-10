"""
Phase 9 — Prompt Registry
Stores all system prompts in a versioned Postgres table.
Supports: create, activate, rollback, shadow mode (% traffic split).
"""

import os
import json
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql://pocketwallet:localdev@localhost:5432/pocketwallet"
)


def get_connection():
    return psycopg2.connect(POSTGRES_URL)


# ── Table setup ───────────────────────────────────────────────────────────────
def init_prompt_table():
    """Create prompt_versions table if it does not exist."""
    sql = """
    CREATE TABLE IF NOT EXISTS prompt_versions (
        id           BIGSERIAL PRIMARY KEY,
        prompt_key   TEXT NOT NULL,
        version      INTEGER NOT NULL,
        content      TEXT NOT NULL,
        description  TEXT,
        is_active    BOOLEAN NOT NULL DEFAULT FALSE,
        shadow_pct   INTEGER NOT NULL DEFAULT 0,
        created_by   TEXT NOT NULL DEFAULT 'system',
        created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (prompt_key, version)
    );

    CREATE INDEX IF NOT EXISTS idx_prompt_key
        ON prompt_versions (prompt_key, is_active);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print("prompt_versions table ready")


def seed_default_prompts():
    """Seed the initial prompt versions."""
    prompts = [
        {
            "prompt_key":  "answer_generation",
            "version":     1,
            "description": "v1 — Formal policy-first tone",
            "content": """You are a helpful customer support agent for PocketWallet, a Pakistani fintech app.
Respond in {language}. If the customer wrote in Roman Urdu, respond in Roman Urdu.
Customer sentiment is {sentiment} — adjust your tone accordingly.

Use the policy context and tool result below to answer the customer accurately.
Always cite your source at the end: Source: <doc_title>, <section>

Policy context:
{policy_context}

Tool result:
{tool_result}

Customer message: {message}

Provide a clear, concise answer in 2-4 sentences. End with the source citation.""",
            "is_active":  True,
            "shadow_pct": 0,
        },
        {
            "prompt_key":  "answer_generation",
            "version":     2,
            "description": "v2 — Empathetic customer-first tone",
            "content": """You are a warm, empathetic customer support agent for PocketWallet, a Pakistani fintech app.
Respond in {language}. If the customer wrote in Roman Urdu, respond in Roman Urdu.
The customer is feeling {sentiment} — be especially kind if they are frustrated or angry.

Use the policy context and tool result below to answer accurately.
Always end with: Source: <doc_title>, <section>

Policy context:
{policy_context}

Tool result:
{tool_result}

Customer message: {message}

Respond warmly and clearly in 2-4 sentences. Acknowledge their concern if upset.""",
            "is_active":  False,
            "shadow_pct": 10,
        },
        {
            "prompt_key":  "intent_detection",
            "version":     1,
            "description": "v1 — Standard intent classifier",
            "content": """You are an intent classification system for PocketWallet, a Pakistani fintech app.
Classify the customer message into exactly one of these intents:
- card_freeze, balance_inquiry, transfer, dispute, kyc_verification, fee_inquiry, general

Respond ONLY with valid JSON:
{{"intent": "<intent_name>", "confidence": <0.0-1.0>, "reason": "<one short sentence>"}}

Customer message: {message}""",
            "is_active":  True,
            "shadow_pct": 0,
        },
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            for p in prompts:
                cur.execute("""
                    INSERT INTO prompt_versions
                        (prompt_key, version, content, description,
                         is_active, shadow_pct, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (prompt_key, version) DO NOTHING
                """, (
                    p["prompt_key"], p["version"], p["content"],
                    p["description"], p["is_active"], p["shadow_pct"],
                    "system"
                ))
        conn.commit()
    print("Default prompts seeded")


# ── Registry operations ───────────────────────────────────────────────────────
def get_active_prompt(prompt_key: str) -> dict | None:
    """Get the currently active prompt for a key."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM prompt_versions
                WHERE prompt_key = %s AND is_active = TRUE
                ORDER BY version DESC LIMIT 1
            """, (prompt_key,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_shadow_prompt(prompt_key: str) -> dict | None:
    """Get shadow prompt if one exists with shadow_pct > 0."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM prompt_versions
                WHERE prompt_key = %s AND shadow_pct > 0 AND is_active = FALSE
                ORDER BY version DESC LIMIT 1
            """, (prompt_key,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_prompt_for_request(prompt_key: str, request_id: int = 0) -> dict:
    """
    Get the prompt to use for a request.
    If a shadow prompt exists, route request_id % 100 < shadow_pct to shadow.
    """
    shadow = get_shadow_prompt(prompt_key)
    if shadow and (request_id % 100) < shadow["shadow_pct"]:
        shadow["_routing"] = "shadow"
        return shadow

    active = get_active_prompt(prompt_key)
    if active:
        active["_routing"] = "active"
        return active

    return {"content": "", "_routing": "fallback"}


def create_prompt_version(
    prompt_key:  str,
    content:     str,
    description: str,
    created_by:  str = "admin",
) -> dict:
    """Create a new prompt version (does not activate it)."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Get next version number
            cur.execute("""
                SELECT COALESCE(MAX(version), 0) + 1 as next_version
                FROM prompt_versions WHERE prompt_key = %s
            """, (prompt_key,))
            next_version = cur.fetchone()["next_version"]

            cur.execute("""
                INSERT INTO prompt_versions
                    (prompt_key, version, content, description,
                     is_active, shadow_pct, created_by)
                VALUES (%s, %s, %s, %s, FALSE, 0, %s)
                RETURNING *
            """, (prompt_key, next_version, content, description, created_by))
            row = dict(cur.fetchone())
        conn.commit()
    print(f"Created prompt {prompt_key} v{next_version}")
    return row


def activate_prompt(prompt_key: str, version: int, created_by: str = "admin") -> bool:
    """Activate a specific prompt version (deactivates others)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Deactivate all versions
            cur.execute("""
                UPDATE prompt_versions SET is_active = FALSE
                WHERE prompt_key = %s
            """, (prompt_key,))
            # Activate target version
            cur.execute("""
                UPDATE prompt_versions
                SET is_active = TRUE
                WHERE prompt_key = %s AND version = %s
            """, (prompt_key, version))
            if cur.rowcount == 0:
                return False
        conn.commit()
    print(f"Activated prompt {prompt_key} v{version}")
    return True


def list_prompt_versions(prompt_key: str) -> list:
    """List all versions of a prompt."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, prompt_key, version, description,
                       is_active, shadow_pct, created_by, created_at
                FROM prompt_versions
                WHERE prompt_key = %s
                ORDER BY version DESC
            """, (prompt_key,))
            return [dict(r) for r in cur.fetchall()]


def set_shadow_pct(prompt_key: str, version: int, pct: int) -> bool:
    """Set shadow traffic percentage for a prompt version."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE prompt_versions
                SET shadow_pct = %s
                WHERE prompt_key = %s AND version = %s
            """, (pct, prompt_key, version))
            updated = cur.rowcount > 0
        conn.commit()
    print(f"Shadow mode: {prompt_key} v{version} → {pct}% traffic")
    return updated
