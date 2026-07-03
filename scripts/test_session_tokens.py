"""
Phase 2 — Session Token Tests
Verifies token creation, validation, expiry, and tampering detection.
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from security.session_tokens import (
    create_session_token, validate_session_token,
    issue_token, get_token, revoke_token
)

DIVIDER = "-" * 60

def run_test(description: str, result: bool) -> bool:
    status = "PASS" if result else "FAIL"
    print(f"  [{status}] {description}")
    return result


def main():
    print("Phase 2 — Session Token Tests")
    print("=" * 60)
    passed = 0
    total  = 0

    # ── Test 1: Valid token creation and validation ────────────────────────────
    print("\nTest #1: Valid token creation and validation")
    token_data = create_session_token("conv_001", "cust_001", "customer_standard")
    result     = validate_session_token(token_data["token"])

    total += 1; passed += run_test("token is valid",                    result["valid"])
    total += 1; passed += run_test("conversation_id matches",           result["conversation_id"] == "conv_001")
    total += 1; passed += run_test("customer_id matches",               result["customer_id"] == "cust_001")
    total += 1; passed += run_test("profile matches",                   result["profile"] == "customer_standard")
    total += 1; passed += run_test("expires_at is in the future",       result["expires_at"] > time.time())

    # ── Test 2: Tampered token is rejected ────────────────────────────────────
    print("\nTest #2: Tampered token rejected")
    good_token    = token_data["token"]
    tampered      = good_token[:-5] + "XXXXX"
    tamper_result = validate_session_token(tampered)

    total += 1; passed += run_test("tampered token is invalid",         not tamper_result["valid"])
    total += 1; passed += run_test("reason mentions signature",         "signature" in tamper_result["reason"])

    # ── Test 3: Wrong prefix rejected ─────────────────────────────────────────
    print("\nTest #3: Wrong prefix rejected")
    bad_prefix = validate_session_token("Bearer some_random_token")
    total += 1; passed += run_test("wrong prefix token invalid",        not bad_prefix["valid"])

    # ── Test 4: issue/get/revoke flow ─────────────────────────────────────────
    print("\nTest #4: issue → get → revoke flow")
    token = issue_token("conv_002", "cust_002", "customer_full")
    total += 1; passed += run_test("token issued successfully",         token is not None)
    total += 1; passed += run_test("get_token returns same token",      get_token("conv_002") == token)

    revoke_token("conv_002")
    total += 1; passed += run_test("token revoked — get returns None",  get_token("conv_002") is None)

    # ── Test 5: Token carries correct Bearer prefix for MCP servers ───────────
    print("\nTest #5: Token is usable as Bearer token")
    bearer = f"Bearer {token}"
    total += 1; passed += run_test("bearer token starts with session_", "session_" in bearer)

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed}/{total} tests passed")


if __name__ == "__main__":
    main()
