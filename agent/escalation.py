"""
Phase 3 — Escalation Logic
Handles:
1. Forced escalation — sensitive topics always escalate regardless of confidence
2. Fallback routing  — low confidence routes to Groq after PII redaction
3. Escalation context packages — full context bundle for human agents
"""

import os
import json
import requests
from datetime import datetime, timezone

OLLAMA_HOST  = os.getenv("OLLAMA_HOST",  "http://localhost:11434")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.1-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ── Forced escalation topics ──────────────────────────────────────────────────
FORCED_ESCALATION_KEYWORDS = [
    # Legal
    "court order", "legal action", "lawyer", "i will sue", "lawsuit",
    "attorney", "police", "FIA", "FIR",
    # Fraud
    "fraud", "scam", "hacked", "unauthorized access", "identity theft",
    "account takeover",
    # Account closure
    "close my account", "delete my account", "account closure",
    "terminate account",
    # Threats
    "threatening", "blackmail", "harassment",
    # Regulatory
    "SBP complaint", "state bank", "mohtasib",
]

ESCALATION_REASONS = {
    "legal":          "Legal threat or court order detected",
    "fraud":          "Fraud or account takeover reported",
    "account_closure":"Account closure requested",
    "regulatory":     "Regulatory complaint or SBP mention",
    "low_confidence": "Agent confidence below threshold",
    "manual":         "Manual escalation triggered",
}


def check_forced_escalation(message: str) -> dict:
    """
    Check if message contains forced escalation keywords.

    Returns:
    {
        "should_escalate": bool,
        "reason":          str,
        "matched_keywords":list,
    }
    """
    message_lower = message.lower()
    matched       = [kw for kw in FORCED_ESCALATION_KEYWORDS
                     if kw in message_lower]

    if not matched:
        return {"should_escalate": False, "reason": "", "matched_keywords": []}

    # Categorise reason — ORDER MATTERS (most specific first)
    reason = "manual"
    if any(kw in matched for kw in ["close my account", "delete my account",
                                     "account closure", "terminate account"]):
        reason = "account_closure"
    elif any(kw in matched for kw in ["SBP complaint", "state bank", "mohtasib"]):
        reason = "regulatory"
    elif any(kw in matched for kw in ["fraud", "scam", "hacked",
                                       "unauthorized access", "identity theft",
                                       "account takeover"]):
        reason = "fraud"
    elif any(kw in matched for kw in ["court order", "legal action", "lawyer",
                                       "i will sue", "lawsuit", "attorney", "FIR"]):
        reason = "legal"

    return {
        "should_escalate": True,
        "reason":          ESCALATION_REASONS[reason],
        "matched_keywords":matched,
    }


def build_escalation_package(
    conversation_id:    str,
    customer_id:        str,
    message:            str,
    sentiment:          dict,
    intent:             dict,
    confidence:         dict,
    answer:             str,
    escalation_reason:  str,
    conversation_history: list = None,
) -> dict:
    """
    Build a full escalation context package for human agents.
    Contains everything needed to pick up the conversation.
    """
    return {
        "escalation_id":      f"ESC_{conversation_id}_{int(datetime.now().timestamp())}",
        "created_at":         datetime.now(timezone.utc).isoformat(),
        "conversation_id":    conversation_id,
        "customer_id":        customer_id,
        "priority":           _get_priority(sentiment, escalation_reason),
        "escalation_reason":  escalation_reason,
        "last_message":       message,
        "sentiment":          sentiment,
        "intent":             intent,
        "confidence":         confidence,
        "ai_draft_answer":    answer,
        "conversation_history": conversation_history or [],
        "recommended_action": _get_recommended_action(escalation_reason),
    }


def _get_priority(sentiment: dict, reason: str) -> str:
    sent = sentiment.get("sentiment", "neutral")
    if reason in ("legal", "fraud") or sent == "angry":
        return "high"
    elif sent == "frustrated":
        return "medium"
    return "low"


def _get_recommended_action(reason: str) -> str:
    actions = {
        "legal":          "Route to compliance team immediately. Do not make commitments.",
        "fraud":          "Route to fraud team. Freeze account if not already done.",
        "account_closure":"Route to retention team. Understand root cause before processing.",
        "regulatory":     "Route to compliance team. SBP response required within 3 days.",
        "low_confidence": "Agent was uncertain. Review AI answer before sending to customer.",
        "manual":         "Review conversation and respond appropriately.",
    }
    reason_lower = reason.lower()
    if "account closure" in reason_lower:
        return actions["account_closure"]
    if "regulatory" in reason_lower or "sbp" in reason_lower:
        return actions["regulatory"]
    if "fraud" in reason_lower:
        return actions["fraud"]
    if "legal" in reason_lower:
        return actions["legal"]
    if "confidence" in reason_lower:
        return actions["low_confidence"]
    return actions["manual"]


def call_groq_fallback(message: str, policy_context: str) -> dict:
    """
    Route to Groq (Llama 70B) when local confidence is low.
    Message is PII-redacted before this call.
    """
    if not GROQ_API_KEY:
        return {
            "answer":  "Fallback model unavailable — GROQ_API_KEY not set.",
            "model":   "none",
            "success": False,
        }

    system_prompt = (
        "You are a helpful customer support agent for PocketWallet, "
        "a Pakistani fintech app. Use the policy context to answer accurately. "
        "Always cite your source."
    )
    user_prompt = (
        f"Policy context:\n{policy_context}\n\n"
        f"Customer question: {message}"
    )

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "model":    GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                "max_tokens": 500,
            },
            timeout=15,
        )
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"]
        return {"answer": answer, "model": GROQ_MODEL, "success": True}

    except Exception as e:
        return {
            "answer":  f"Fallback model error: {e}",
            "model":   GROQ_MODEL,
            "success": False,
        }