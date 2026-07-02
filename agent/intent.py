"""
Phase 1 — Intent Detection
Classifies customer message into one of 7 support intents.
Uses Ollama LLM with a structured prompt returning JSON.
"""

import os
import json
import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL   = os.getenv("LLM_MODEL", "llama3.1:8b")

INTENTS = [
    "card_freeze",        # freeze/block/lost/stolen card
    "balance_inquiry",    # check balance, available funds
    "transfer",           # send money, IBFT, transfer limits
    "dispute",            # dispute transaction, chargeback, unauthorized charge
    "kyc_verification",   # KYC status, document upload, account tier
    "fee_inquiry",        # fees, charges, costs
    "general",            # anything that does not fit above
]

PROMPT = """You are an intent classification system for PocketWallet, a Pakistani fintech app.
Classify the customer message into exactly one of these intents:

- card_freeze: customer wants to freeze, block, or report lost/stolen card
- balance_inquiry: customer wants to check their balance or available funds
- transfer: customer wants to send money, ask about transfer limits or IBFT
- dispute: customer wants to dispute a transaction, report unauthorized charge, or chargeback
- kyc_verification: customer asking about KYC status, document upload, or account tier limits
- fee_inquiry: customer asking about fees, charges, or costs
- general: does not fit any of the above

Respond ONLY with valid JSON in this exact format:
{{"intent": "<intent_name>", "confidence": <0.0-1.0>, "reason": "<one short sentence>"}}

Customer message: {message}"""


def detect_intent(message: str) -> dict:
    """
    Returns: {
        "intent":     one of INTENTS,
        "confidence": float,
        "reason":     str
    }
    """
    resp = requests.post(f"{OLLAMA_HOST}/api/generate", json={
        "model":  LLM_MODEL,
        "prompt": PROMPT.format(message=message),
        "stream": False,
        "format": "json"
    })
    resp.raise_for_status()

    raw    = resp.json()["response"]
    result = json.loads(raw)

    intent = result.get("intent", "general").lower()
    if intent not in INTENTS:
        intent = "general"

    return {
        "intent":     intent,
        "confidence": float(result.get("confidence", 0.8)),
        "reason":     result.get("reason", "")
    }
