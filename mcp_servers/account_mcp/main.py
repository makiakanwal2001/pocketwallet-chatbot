"""
Account MCP Server — Port 8001
Tools: check_balance, get_account_info
"""

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Account MCP Server", version="1.0.0")

# ── Mock customer data ────────────────────────────────────────────────────────
ACCOUNTS = {
    "cust_001": {
        "name":          "Ayesha Malik",
        "balance_pkr":   45230.50,
        "account_status":"active",
        "kyc_tier":      1,
        "account_age_days": 120,
        "daily_limit_pkr":  200000,
        "monthly_spent_pkr": 12400,
    },
    "cust_002": {
        "name":          "Bilal Ahmed",
        "balance_pkr":   3200.00,
        "account_status":"active",
        "kyc_tier":      0,
        "account_age_days": 3,
        "daily_limit_pkr":  25000,
        "monthly_spent_pkr": 800,
    },
    "cust_003": {
        "name":          "Sara Khan",
        "balance_pkr":   128000.00,
        "account_status":"frozen",
        "kyc_tier":      2,
        "account_age_days": 450,
        "daily_limit_pkr":  1000000,
        "monthly_spent_pkr": 95000,
    },
}

# ── Auth (simple token check — full security in Phase 2) ─────────────────────
def verify_token(token: str | None):
    if not token or not token.startswith("Bearer session_"):
        raise HTTPException(status_code=401, detail="Invalid or missing session token")

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "account_mcp"}


@app.get("/check_balance/{customer_id}")
def check_balance(customer_id: str, authorization: str | None = Header(None)):
    verify_token(authorization)
    account = ACCOUNTS.get(customer_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return {
        "customer_id":   customer_id,
        "name":          account["name"],
        "balance_pkr":   account["balance_pkr"],
        "account_status":account["account_status"],
        "kyc_tier":      account["kyc_tier"],
    }


@app.get("/get_account_info/{customer_id}")
def get_account_info(customer_id: str, authorization: str | None = Header(None)):
    verify_token(authorization)
    account = ACCOUNTS.get(customer_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return {"customer_id": customer_id, **account}
