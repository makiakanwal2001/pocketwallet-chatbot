"""
Phase 8 — User Segmentation
Groups customers by behavior based on their event history.
Segments: new_signup, kyc_pending, activation_incomplete,
          inactive_14d, high_value, at_risk
"""

import os
import json
import redis
from datetime import datetime, timezone, timedelta
from growth.events import get_redis, get_customer_events

# ── Segment definitions ───────────────────────────────────────────────────────
SEGMENTS = {
    "new_signup": {
        "description": "Signed up in last 7 days, no first transaction",
        "lifecycle_stage": "onboarding",
    },
    "kyc_pending": {
        "description": "KYC incomplete — documents not uploaded",
        "lifecycle_stage": "activation",
    },
    "activation_incomplete": {
        "description": "KYC done but no first transfer in 7 days",
        "lifecycle_stage": "activation",
    },
    "inactive_14d": {
        "description": "No transaction in last 14 days",
        "lifecycle_stage": "re_engagement",
    },
    "high_value": {
        "description": "Regular transactions, Tier 2 KYC",
        "lifecycle_stage": "retention",
    },
    "at_risk": {
        "description": "Multiple failed transfers or disputes",
        "lifecycle_stage": "win_back",
    },
}

# ── Mock customer profiles (Phase 5 would pull from Postgres) ─────────────────
CUSTOMER_PROFILES = {
    "cust_001": {
        "name":              "Ayesha Malik",
        "kyc_tier":          1,
        "signup_date":       "2026-04-01",
        "last_transaction":  "2026-07-01",
        "transaction_count": 45,
        "failed_transfers":  0,
        "open_disputes":     0,
    },
    "cust_002": {
        "name":              "Bilal Ahmed",
        "kyc_tier":          0,
        "signup_date":       "2026-07-01",
        "last_transaction":  None,
        "transaction_count": 0,
        "failed_transfers":  2,
        "open_disputes":     0,
    },
    "cust_003": {
        "name":              "Sara Khan",
        "kyc_tier":          2,
        "signup_date":       "2025-05-15",
        "last_transaction":  "2026-06-20",
        "transaction_count": 120,
        "failed_transfers":  0,
        "open_disputes":     1,
    },
}


def get_customer_segment(customer_id: str) -> dict:
    """
    Determine which segment a customer belongs to.

    Returns:
    {
        "customer_id": str,
        "segment":     str,
        "reason":      str,
        "lifecycle_stage": str,
    }
    """
    profile = CUSTOMER_PROFILES.get(customer_id)
    if not profile:
        return {
            "customer_id":    customer_id,
            "segment":        "unknown",
            "reason":         "No profile found",
            "lifecycle_stage":"unknown",
        }

    now           = datetime.now(timezone.utc).date()
    signup_date   = datetime.strptime(profile["signup_date"], "%Y-%m-%d").date()
    days_since_signup = (now - signup_date).days

    last_txn      = profile.get("last_transaction")
    days_inactive = None
    if last_txn:
        last_txn_date = datetime.strptime(last_txn, "%Y-%m-%d").date()
        days_inactive = (now - last_txn_date).days

    # Segment logic — order matters (most specific first)
    if profile["kyc_tier"] == 0:
        segment = "kyc_pending"
        reason  = "KYC not completed — no documents uploaded"

    elif profile["transaction_count"] == 0 and days_since_signup <= 7:
        segment = "activation_incomplete"
        reason  = f"Signed up {days_since_signup} days ago but no first transfer"

    elif days_inactive is not None and days_inactive >= 14:
        segment = "inactive_14d"
        reason  = f"No transaction for {days_inactive} days"

    elif profile["failed_transfers"] >= 2 or profile["open_disputes"] >= 1:
        segment = "at_risk"
        reason  = (f"{profile['failed_transfers']} failed transfers, "
                   f"{profile['open_disputes']} open disputes")

    elif profile["kyc_tier"] >= 2 and profile["transaction_count"] >= 50:
        segment = "high_value"
        reason  = f"Tier {profile['kyc_tier']} KYC, {profile['transaction_count']} transactions"

    elif days_since_signup <= 7:
        segment = "new_signup"
        reason  = f"New customer — signed up {days_since_signup} days ago"

    else:
        segment = "high_value"
        reason  = "Active customer with good standing"

    return {
        "customer_id":    customer_id,
        "name":           profile["name"],
        "segment":        segment,
        "reason":         reason,
        "lifecycle_stage":SEGMENTS[segment]["lifecycle_stage"],
        "description":    SEGMENTS[segment]["description"],
    }


def segment_all_customers() -> dict:
    """Segment all known customers and return a summary."""
    results     = {}
    segment_counts = {s: [] for s in SEGMENTS}

    for customer_id in CUSTOMER_PROFILES:
        seg = get_customer_segment(customer_id)
        results[customer_id] = seg
        segment_counts[seg["segment"]].append(customer_id)

    return {
        "segments":      results,
        "summary":       {k: len(v) for k, v in segment_counts.items()},
        "customer_lists":segment_counts,
    }
