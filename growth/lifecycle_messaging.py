"""
Phase 8 — Lifecycle Messaging
Generates automated messages triggered by customer segments.
Messages: onboarding, activation, re-engagement, win-back.
"""

import os
import json
import requests
from datetime import datetime, timezone
from growth.segmentation import get_customer_segment, CUSTOMER_PROFILES

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL   = os.getenv("LLM_MODEL",   "llama3.1:8b")

# ── Message templates per segment ─────────────────────────────────────────────
MESSAGE_TEMPLATES = {
    "new_signup": {
        "channel":  "in_app",
        "subject":  "Welcome to PocketWallet!",
        "prompt":   """Write a warm, friendly welcome message for a new PocketWallet customer named {name}.
Keep it under 3 sentences. Mention: (1) they can complete KYC to unlock transfers,
(2) their first 3 IBFT transfers are free. End with a clear call to action."""
    },
    "kyc_pending": {
        "channel":  "push_notification",
        "subject":  "Complete your verification",
        "prompt":   """Write a short push notification (max 2 sentences) for {name} who has not completed KYC yet.
They are missing: {missing_docs}. Make it friendly and urgent. 
Mention they are currently limited to PKR 10,000 balance until verified."""
    },
    "activation_incomplete": {
        "channel":  "in_app",
        "subject":  "Make your first transfer",
        "prompt":   """Write a friendly in-app message for {name} who signed up but has not made their first transfer yet.
Keep it under 3 sentences. Mention: (1) first 3 IBFT transfers are free,
(2) they can send money instantly to any bank. Include a clear call to action."""
    },
    "inactive_14d": {
        "channel":  "push_notification",
        "subject":  "We miss you!",
        "prompt":   """Write a re-engagement push notification for {name} who has not used PocketWallet in 14+ days.
Max 2 sentences. Be warm and welcoming. Mention a benefit to come back
(e.g. free transfers, instant payments). Do not be pushy."""
    },
    "at_risk": {
        "channel":  "in_app",
        "subject":  "We are here to help",
        "prompt":   """Write an empathetic in-app message for {name} who has had issues with PocketWallet
(failed transfers or open disputes). Max 3 sentences. Acknowledge the frustration,
offer help, and provide a clear next step (contact support or check dispute status)."""
    },
    "high_value": {
        "channel":  "in_app",
        "subject":  "Thank you for being a valued customer",
        "prompt":   """Write a short appreciation message for {name}, a loyal PocketWallet customer
with many transactions. Max 2 sentences. Make them feel valued and mention
a benefit they may not know about (e.g. Tier 2 KYC unlocks higher limits)."""
    },
}


def generate_message(customer_id: str) -> dict:
    """
    Generate a personalised lifecycle message for a customer
    based on their segment.

    Returns:
    {
        "customer_id": str,
        "segment":     str,
        "channel":     str,
        "subject":     str,
        "message":     str,
        "generated_at":str,
    }
    """
    seg      = get_customer_segment(customer_id)
    profile  = CUSTOMER_PROFILES.get(customer_id, {})
    segment  = seg["segment"]
    template = MESSAGE_TEMPLATES.get(segment, MESSAGE_TEMPLATES["new_signup"])

    # Build prompt with customer context
    missing_docs = "CNIC front, CNIC back, selfie" if seg.get("kyc_tier", 1) == 0 else "pending documents"
    prompt = template["prompt"].format(
        name         = profile.get("name", "valued customer"),
        missing_docs = missing_docs,
    )

    # Generate with local LLM
    resp = requests.post(f"{OLLAMA_HOST}/api/generate", json={
        "model":  LLM_MODEL,
        "prompt": prompt,
        "stream": False,
    })
    resp.raise_for_status()
    message_text = resp.json()["response"].strip()

    return {
        "customer_id":  customer_id,
        "name":         profile.get("name", ""),
        "segment":      segment,
        "channel":      template["channel"],
        "subject":      template["subject"],
        "message":      message_text,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def run_lifecycle_campaign(customer_ids: list = None) -> list:
    """
    Generate lifecycle messages for a list of customers.
    If no list provided, runs for all known customers.
    """
    from growth.segmentation import CUSTOMER_PROFILES
    targets  = customer_ids or list(CUSTOMER_PROFILES.keys())
    results  = []

    print(f"\nRunning lifecycle campaign for {len(targets)} customers...")
    for cid in targets:
        msg = generate_message(cid)
        results.append(msg)
        print(f"  [{msg['segment']}] {msg['name']} → {msg['channel']}: {msg['subject']}")

    return results
