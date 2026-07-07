"""
Phase 5 — Backend Config
Central config for JWT, roles, and database.
"""

import os

# ── JWT ───────────────────────────────────────────────────────────────────────
JWT_SECRET      = os.getenv("JWT_SECRET", "dev_jwt_secret_changeme_in_production")
JWT_ALGORITHM   = "HS256"
JWT_EXPIRE_MINS = int(os.getenv("JWT_EXPIRE_MINS", "60"))

# ── Roles ─────────────────────────────────────────────────────────────────────
ROLE_CUSTOMER = "customer"
ROLE_AGENT    = "agent"
ROLE_ADMIN    = "admin"

ROLES = [ROLE_CUSTOMER, ROLE_AGENT, ROLE_ADMIN]

# ── Database ──────────────────────────────────────────────────────────────────
POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql://pocketwallet:localdev@localhost:5432/pocketwallet"
)
