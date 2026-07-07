"""
Phase 5 — Database Setup
Creates users table and seeds demo users for all three roles.
"""

import psycopg2
import psycopg2.extras
from backend.config import POSTGRES_URL


def get_connection():
    return psycopg2.connect(POSTGRES_URL)


def init_tables():
    """Create users and conversations tables if they do not exist."""
    sql = """
    CREATE TABLE IF NOT EXISTS users (
        id           BIGSERIAL PRIMARY KEY,
        username     TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role         TEXT NOT NULL CHECK (role IN ('customer','agent','admin')),
        customer_id  TEXT,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS conversations (
        id              BIGSERIAL PRIMARY KEY,
        conversation_id TEXT UNIQUE NOT NULL,
        customer_id     TEXT NOT NULL,
        username        TEXT NOT NULL,
        messages        JSONB NOT NULL DEFAULT '[]',
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print("Tables ready: users, conversations")


def seed_demo_users(password_hash_fn):
    """Seed one user per role for demo/testing purposes."""
    demo_users = [
        ("ayesha",  password_hash_fn("customer123"), "customer", "cust_001"),
        ("bilal",   password_hash_fn("customer123"), "customer", "cust_002"),
        ("sara",    password_hash_fn("customer123"), "customer", "cust_003"),
        ("agent01", password_hash_fn("agent123"),    "agent",    None),
        ("admin01", password_hash_fn("admin123"),    "admin",    None),
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            for username, pw_hash, role, cust_id in demo_users:
                cur.execute("""
                    INSERT INTO users (username, password_hash, role, customer_id)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                """, (username, pw_hash, role, cust_id))
        conn.commit()
    print("Demo users seeded: ayesha, bilal, sara, agent01, admin01")


def get_user(username: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            return dict(row) if row else None


def save_conversation(conversation_id: str, customer_id: str,
                      username: str, messages: list):
    with get_connection() as conn:
        with conn.cursor() as cur:
            import json
            cur.execute("""
                INSERT INTO conversations
                    (conversation_id, customer_id, username, messages)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (conversation_id) DO UPDATE
                SET messages   = EXCLUDED.messages,
                    updated_at = NOW()
            """, (conversation_id, customer_id, username, json.dumps(messages)))
        conn.commit()


def get_conversations(username: str, role: str,
                      customer_id: str = None) -> list:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if role == "admin":
                cur.execute("""
                    SELECT conversation_id, customer_id, username,
                           messages, created_at, updated_at
                    FROM conversations ORDER BY updated_at DESC
                """)
            elif role == "agent":
                cur.execute("""
                    SELECT conversation_id, customer_id, username,
                           messages, created_at, updated_at
                    FROM conversations ORDER BY updated_at DESC
                """)
            else:
                cur.execute("""
                    SELECT conversation_id, customer_id, username,
                           messages, created_at, updated_at
                    FROM conversations
                    WHERE username = %s
                    ORDER BY updated_at DESC
                """, (username,))
            return [dict(r) for r in cur.fetchall()]
