"""
Phase 2 — Audit Log Test
Initialises the table, writes several event types,
then reads them back to verify correctness.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from security.audit_log import (
    init_audit_table,
    log_tool_call, log_tool_blocked,
    log_pii_detected, log_session_issued, log_session_revoked,
    get_logs_for_conversation, get_logs_for_customer,
)
import time

CONV_ID = "conv_audit_test_001"
CUST_ID = "cust_001"
DIVIDER = "=" * 60


def run_test(description: str, result: bool) -> bool:
    status = "PASS" if result else "FAIL"
    print(f"  [{status}] {description}")
    return result


def main():
    print("Phase 2 — Audit Log Tests")
    print(DIVIDER)

    # 1. Init table
    print("\nInitialising audit_log table...")
    init_audit_table()

    passed = 0
    total  = 0

    # 2. Write events
    print("\nWriting audit events...")
    log_session_issued(CONV_ID, CUST_ID, "customer_standard", time.time() + 3600)
    print("  [wrote] session_issued")

    log_pii_detected(CONV_ID, CUST_ID, ["PK_CNIC", "PHONE"], 2)
    print("  [wrote] pii_detected")

    log_tool_call(CONV_ID, CUST_ID, "check_balance", "account",
                  "customer_standard", "balance: PKR 45,230")
    print("  [wrote] tool_call — check_balance")

    log_tool_call(CONV_ID, CUST_ID, "freeze_card", "card",
                  "customer_standard", "card ending 4821 frozen")
    print("  [wrote] tool_call — freeze_card")

    log_tool_blocked(CONV_ID, CUST_ID, "kyc_aml_check", "compliance",
                     "customer_standard", "compliance server not in scope")
    print("  [wrote] tool_blocked — kyc_aml_check")

    log_session_revoked(CONV_ID, CUST_ID)
    print("  [wrote] session_revoked")

    # 3. Read back and verify
    print(f"\nReading logs for conversation: {CONV_ID}")
    logs = get_logs_for_conversation(CONV_ID)

    total += 1; passed += run_test(
        "6 events written and retrieved",
        len(logs) >= 6
    )

    event_types = [l["event_type"] for l in logs]
    total += 1; passed += run_test(
        "session_issued event present",
        "session_issued" in event_types
    )
    total += 1; passed += run_test(
        "pii_detected event present",
        "pii_detected" in event_types
    )
    total += 1; passed += run_test(
        "tool_call events present",
        event_types.count("tool_call") >= 2
    )
    total += 1; passed += run_test(
        "tool_blocked event present",
        "tool_blocked" in event_types
    )
    total += 1; passed += run_test(
        "session_revoked event present",
        "session_revoked" in event_types
    )

    # 4. Check tool_blocked details
    blocked = next((l for l in logs if l["event_type"] == "tool_blocked"), None)
    total += 1; passed += run_test(
        "blocked tool name is kyc_aml_check",
        blocked and blocked["tool_name"] == "kyc_aml_check"
    )
    total += 1; passed += run_test(
        "blocked server is compliance",
        blocked and blocked["server_name"] == "compliance"
    )

    # 5. Customer-level query
    print(f"\nReading logs for customer: {CUST_ID}")
    cust_logs = get_logs_for_customer(CUST_ID, limit=20)
    total += 1; passed += run_test(
        "customer logs returned",
        len(cust_logs) > 0
    )

    # 6. Print a sample log entry
    print(f"\nSample log entry:")
    sample = logs[-1]
    for k, v in sample.items():
        print(f"  {k}: {v}")

    print(f"\n{DIVIDER}")
    print(f"RESULTS: {passed}/{total} tests passed")


if __name__ == "__main__":
    main()
