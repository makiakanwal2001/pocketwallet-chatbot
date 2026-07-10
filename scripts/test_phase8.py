"""
Phase 8 — Growth Automation Tests
Tests: event tracking, user segmentation, lifecycle messaging.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from growth.events           import (publish_event, get_customer_events,
                                      event_signup, event_kyc_incomplete,
                                      event_transfer_failed, event_inactive_14d,
                                      event_first_transaction)
from growth.segmentation     import get_customer_segment, segment_all_customers
from growth.lifecycle_messaging import generate_message, run_lifecycle_campaign

DIVIDER = "=" * 65

def run_test(desc: str, result: bool) -> bool:
    print(f"  {'[PASS]' if result else '[FAIL]'} {desc}")
    return result


def test_event_tracking():
    print(f"\n{DIVIDER}")
    print("Test 1: Event Tracking (Redis Pub/Sub)")
    print(DIVIDER)

    passed = True
    try:
        # Fire several events
        event_signup("cust_002", channel="mobile_app")
        event_kyc_incomplete("cust_002", missing_docs=["CNIC front", "CNIC back", "selfie"])
        event_transfer_failed("cust_002", reason="insufficient_funds", amount_pkr=5000)
        event_inactive_14d("cust_001", last_transaction="2026-06-20")
        event_first_transaction("cust_001", amount_pkr=1500)

        # Verify events stored in Redis
        cust_002_events = get_customer_events("cust_002", limit=10)
        cust_001_events = get_customer_events("cust_001", limit=10)

        passed &= run_test("cust_002 events published to Redis",
                           len(cust_002_events) >= 3)
        passed &= run_test("cust_001 events published to Redis",
                           len(cust_001_events) >= 2)
        passed &= run_test("events have correct structure",
                           all("event_type" in e and "customer_id" in e
                               for e in cust_002_events))
        passed &= run_test("transfer_failed event recorded",
                           any(e["event_type"] == "transfer_failed"
                               for e in cust_002_events))

        print(f"\n  Recent events for cust_002:")
        for e in cust_002_events[:3]:
            print(f"    → {e['event_type']} at {e['timestamp'][:19]}")

    except Exception as ex:
        print(f"  [FAIL] Event tracking error: {ex}")
        passed = False

    return passed


def test_segmentation():
    print(f"\n{DIVIDER}")
    print("Test 2: User Segmentation")
    print(DIVIDER)

    passed = True
    try:
        # Individual segments
        seg_001 = get_customer_segment("cust_001")
        seg_002 = get_customer_segment("cust_002")
        seg_003 = get_customer_segment("cust_003")

        print(f"\n  Segments:")
        for seg in [seg_001, seg_002, seg_003]:
            print(f"    {seg['name']:<15} → {seg['segment']:<25} ({seg['reason']})")

        passed &= run_test("cust_002 segmented as kyc_pending",
                           seg_002["segment"] == "kyc_pending")
        passed &= run_test("all segments have lifecycle_stage",
                           all("lifecycle_stage" in s
                               for s in [seg_001, seg_002, seg_003]))

        # Full segmentation run
        all_segs = segment_all_customers()
        passed &= run_test("all customers segmented",
                           len(all_segs["segments"]) == 3)
        passed &= run_test("summary counts are correct",
                           sum(all_segs["summary"].values()) == 3)

        print(f"\n  Segment summary:")
        for seg, count in all_segs["summary"].items():
            if count > 0:
                print(f"    {seg:<25} → {count} customer(s)")

    except Exception as ex:
        print(f"  [FAIL] Segmentation error: {ex}")
        passed = False

    return passed


def test_lifecycle_messaging():
    print(f"\n{DIVIDER}")
    print("Test 3: Lifecycle Messaging")
    print(DIVIDER)

    passed = True
    try:
        print("\n  Generating messages for all 3 customers...")
        results = run_lifecycle_campaign()

        passed &= run_test("messages generated for all customers",
                           len(results) == 3)
        passed &= run_test("all messages have content",
                           all(len(r["message"]) > 20 for r in results))
        passed &= run_test("all messages have channel assigned",
                           all(r["channel"] in ["in_app", "push_notification"]
                               for r in results))

        print(f"\n  Generated messages:")
        for r in results:
            print(f"\n  [{r['segment']}] {r['name']} → {r['channel']}")
            print(f"  Subject: {r['subject']}")
            print(f"  Message: {r['message'][:150]}...")

    except Exception as ex:
        print(f"  [FAIL] Lifecycle messaging error: {ex}")
        passed = False

    return passed


def main():
    print(DIVIDER)
    print("PocketWallet — Phase 8 Growth Automation Tests")
    print(DIVIDER)

    results = [
        test_event_tracking(),
        test_segmentation(),
        test_lifecycle_messaging(),
    ]

    passed = sum(results)
    total  = len(results)

    print(f"\n{DIVIDER}")
    print(f"RESULTS: {passed}/{total} tests passed")
    print(f"Phase 8 DoD: {'MET ✓' if passed == total else 'NOT MET ✗'}")
    print(DIVIDER)


if __name__ == "__main__":
    main()
