"""
Phase 5 — FastAPI Backend
JWT auth + three-role RBAC (customer, agent, admin).
All endpoints demonstrated via curl — no frontend yet.
"""

import uuid
import json
import glob
import os
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from backend.config   import ROLE_CUSTOMER, ROLE_AGENT, ROLE_ADMIN
from backend.auth     import (hash_password, verify_password,
                               create_access_token, get_current_user,
                               require_role)
from backend.database import (init_tables, seed_demo_users, get_user,
                               save_conversation, get_conversations)
from security.audit_log     import (init_audit_table, log_tool_call,
                                     get_logs_for_customer)
from security.pii_redaction import redact
from security.mcp_scope     import create_scope
from security.session_tokens import issue_token
from agent.escalation       import check_forced_escalation

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent.graph import run_agent

app = FastAPI(title="PocketWallet API", version="1.0.0")

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_tables()
    init_audit_table()
    seed_demo_users(hash_password)
    print("PocketWallet API ready")


# ── Schemas ───────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str


class ClaimRequest(BaseModel):
    note: str = ""


# ── Auth endpoints ────────────────────────────────────────────────────────────
@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form.username)
    if not user or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    token = create_access_token({
        "sub":         user["username"],
        "role":        user["role"],
        "customer_id": user["customer_id"],
    })
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


@app.get("/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    return {
        "username":    current_user["sub"],
        "role":        current_user["role"],
        "customer_id": current_user.get("customer_id"),
    }


# ── Customer endpoints ────────────────────────────────────────────────────────
@app.post("/chat")
def chat(
    req:          ChatRequest,
    current_user: dict = Depends(require_role(ROLE_CUSTOMER, ROLE_AGENT, ROLE_ADMIN))
):
    """POST /chat — send a message and get an AI response."""
    customer_id     = current_user.get("customer_id") or "cust_001"
    username        = current_user["sub"]
    conversation_id = f"conv_{username}_{uuid.uuid4().hex[:8]}"

    # 1. PII redaction
    redaction    = redact(req.message)
    safe_message = redaction["redacted"]

    # 2. Forced escalation check
    forced = check_forced_escalation(req.message)

    # 3. Issue session token + create scope
    session_token = issue_token(conversation_id, customer_id, "customer_standard")
    create_scope(conversation_id, customer_id, "customer_standard")

    # 4. Run agent
    result = run_agent(safe_message, customer_id)

    # 5. Log tool call if any
    if result.get("tool_called") and result["tool_called"] != "none":
        log_tool_call(
            conversation_id = conversation_id,
            customer_id     = customer_id,
            tool_name       = result["tool_called"],
            server_name     = result["tool_called"].split("_")[0],
            profile         = "customer_standard",
            result_summary  = "ok",
        )

    # 6. Save conversation
    messages = [
        {"role": "user",      "content": req.message,      "timestamp": datetime.now(timezone.utc).isoformat()},
        {"role": "assistant", "content": result["answer"],  "timestamp": datetime.now(timezone.utc).isoformat()},
    ]
    save_conversation(conversation_id, customer_id, username, messages)

    return {
        "conversation_id": conversation_id,
        "message":         req.message,
        "answer":          result["answer"],
        "intent":          result["intent"]["intent"],
        "sentiment":       result["sentiment"]["sentiment"],
        "tool_called":     result["tool_called"],
        "citations":       result["citations"],
        "escalated":       forced["should_escalate"],
        "escalation_reason": forced["reason"] if forced["should_escalate"] else None,
        "pii_detected":    redaction["pii_count"] > 0,
    }


@app.get("/conversations")
def list_conversations(
    current_user: dict = Depends(require_role(ROLE_CUSTOMER, ROLE_AGENT, ROLE_ADMIN))
):
    """GET /conversations — customers see own only, agents/admins see all."""
    return get_conversations(
        username    = current_user["sub"],
        role        = current_user["role"],
        customer_id = current_user.get("customer_id"),
    )


# ── Agent endpoints ───────────────────────────────────────────────────────────
@app.get("/escalations")
def get_escalations(
    current_user: dict = Depends(require_role(ROLE_AGENT, ROLE_ADMIN))
):
    """GET /escalations — agent and admin only."""
    results_dir = os.path.join(os.path.dirname(__file__), "..", "eval", "results")
    escalations = []
    if os.path.exists(results_dir):
        files = sorted(glob.glob(f"{results_dir}/eval_*.json"))
        if files:
            with open(files[-1]) as f:
                data = json.load(f)
            failed = [r for r in data.get("results", [])
                      if not r.get("passed")]
            escalations = failed[:10]
    return {
        "role":        current_user["role"],
        "escalations": escalations,
        "count":       len(escalations),
    }


@app.post("/escalations/{escalation_id}/claim")
def claim_escalation(
    escalation_id: str,
    req:           ClaimRequest,
    current_user:  dict = Depends(require_role(ROLE_AGENT, ROLE_ADMIN))
):
    """POST /escalations/{id}/claim — agent claims an escalation."""
    return {
        "escalation_id": escalation_id,
        "claimed_by":    current_user["sub"],
        "note":          req.note,
        "status":        "claimed",
        "timestamp":     datetime.now(timezone.utc).isoformat(),
    }


# ── Admin endpoints ───────────────────────────────────────────────────────────
@app.get("/audit-log")
def get_audit_log(
    current_user: dict = Depends(require_role(ROLE_ADMIN))
):
    """GET /audit-log — admin only."""
    logs = get_logs_for_customer("cust_001", limit=20)
    return {"role": current_user["role"], "logs": logs, "count": len(logs)}


@app.get("/eval-results")
def get_eval_results(
    current_user: dict = Depends(require_role(ROLE_ADMIN))
):
    """GET /eval-results — admin only."""
    results_dir = os.path.join(os.path.dirname(__file__), "..", "eval", "results")
    files = sorted(glob.glob(f"{results_dir}/eval_*.json"))
    if not files:
        return {"message": "No eval results found"}
    with open(files[-1]) as f:
        data = json.load(f)
    return {
        "role":      current_user["role"],
        "timestamp": data["timestamp"],
        "pass_rate": data["pass_rate"],
        "total":     data["total"],
        "passed":    data["passed"],
        "failed":    data["failed"],
        "categories":data["categories"],
    }


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "pocketwallet-api", "version": "1.0.0"}
