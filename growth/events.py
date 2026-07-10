"""
Phase 8 — Event Tracking
Product events fire into Redis Pub/Sub when key things happen.
Events: signup, kyc_incomplete, transfer_failed, first_transaction,
        card_blocked, inactive_14d, dispute_opened
"""

import os
import json
import redis
from datetime import datetime, timezone

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# ── Event types ───────────────────────────────────────────────────────────────
EVENT_SIGNUP            = "signup"
EVENT_KYC_INCOMPLETE    = "kyc_incomplete"
EVENT_KYC_COMPLETE      = "kyc_complete"
EVENT_TRANSFER_FAILED   = "transfer_failed"
EVENT_FIRST_TRANSACTION = "first_transaction"
EVENT_CARD_BLOCKED      = "card_blocked"
EVENT_INACTIVE_14D      = "inactive_14d"
EVENT_DISPUTE_OPENED    = "dispute_opened"
EVENT_ESCALATION        = "escalation"

REDIS_CHANNEL = "pocketwallet:growth_events"

# ── Redis client ──────────────────────────────────────────────────────────────
_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


# ── Event publisher ───────────────────────────────────────────────────────────
def publish_event(
    event_type:  str,
    customer_id: str,
    metadata:    dict = None,
) -> dict:
    """
    Publish a product event to Redis Pub/Sub.

    Returns the event dict that was published.
    """
    event = {
        "event_type":  event_type,
        "customer_id": customer_id,
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "metadata":    metadata or {},
    }

    r = get_redis()
    r.publish(REDIS_CHANNEL, json.dumps(event))

    # Also store in a Redis list for replay/history
    r.lpush(f"events:{customer_id}", json.dumps(event))
    r.ltrim(f"events:{customer_id}", 0, 99)  # keep last 100 events per customer

    print(f"[Event] {event_type} → customer={customer_id}")
    return event


def get_customer_events(customer_id: str, limit: int = 20) -> list:
    """Retrieve recent events for a customer."""
    r = get_redis()
    raw = r.lrange(f"events:{customer_id}", 0, limit - 1)
    return [json.loads(e) for e in raw]


# ── Convenience publishers ────────────────────────────────────────────────────
def event_signup(customer_id: str, channel: str = "app"):
    return publish_event(EVENT_SIGNUP, customer_id, {"channel": channel})

def event_kyc_incomplete(customer_id: str, missing_docs: list = None):
    return publish_event(EVENT_KYC_INCOMPLETE, customer_id,
                        {"missing_docs": missing_docs or []})

def event_kyc_complete(customer_id: str, tier: int = 1):
    return publish_event(EVENT_KYC_COMPLETE, customer_id, {"tier": tier})

def event_transfer_failed(customer_id: str, reason: str = "", amount_pkr: float = 0):
    return publish_event(EVENT_TRANSFER_FAILED, customer_id,
                        {"reason": reason, "amount_pkr": amount_pkr})

def event_first_transaction(customer_id: str, amount_pkr: float = 0):
    return publish_event(EVENT_FIRST_TRANSACTION, customer_id,
                        {"amount_pkr": amount_pkr})

def event_card_blocked(customer_id: str, reason: str = "lost_stolen"):
    return publish_event(EVENT_CARD_BLOCKED, customer_id, {"reason": reason})

def event_inactive_14d(customer_id: str, last_transaction: str = ""):
    return publish_event(EVENT_INACTIVE_14D, customer_id,
                        {"last_transaction": last_transaction})

def event_dispute_opened(customer_id: str, dispute_type: str = "", amount_pkr: float = 0):
    return publish_event(EVENT_DISPUTE_OPENED, customer_id,
                        {"dispute_type": dispute_type, "amount_pkr": amount_pkr})
