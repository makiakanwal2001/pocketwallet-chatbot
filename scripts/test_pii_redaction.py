"""
Phase 2 — PII Redaction Test
Verifies all Pakistani PII types are correctly redacted.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from security.pii_redaction import redact

DIVIDER = "-" * 60

TEST_CASES = [
    {
        "id":          1,
        "description": "CNIC with dashes",
        "input":       "My CNIC is 42101-1234567-8 please verify it.",
        "expect_redacted": "[CNIC_REDACTED]",
    },
    {
        "id":          2,
        "description": "Card number",
        "input":       "My card number is 4111 1111 1111 1111",
        "expect_redacted": "[CARD_REDACTED]",
    },
    {
        "id":          3,
        "description": "Pakistani phone number",
        "input":       "You can call me on 0312-3456789",
        "expect_redacted": "[PHONE_REDACTED]",
    },
    {
        "id":          4,
        "description": "Email address",
        "input":       "My email is ayesha.malik@gmail.com",
        "expect_redacted": "[EMAIL_REDACTED]",
    },
    {
        "id":          5,
        "description": "Multiple PII types in one message",
        "input":       "I am Sara Khan, CNIC 42201-9876543-2, card 5500000000000004, phone 03001234567",
        "expect_redacted": "[CNIC_REDACTED]",
    },
    {
        "id":          6,
        "description": "Clean message — no PII",
        "input":       "What is the fee for sending money to another bank?",
        "expect_redacted": None,
    },
]


def main():
    print("Phase 2 — PII Redaction Tests")
    print("=" * 60)

    passed = 0
    for tc in TEST_CASES:
        result = redact(tc["input"])
        print(f"\nTest #{tc['id']}: {tc['description']}")
        print(f"  Input:    {tc['input']}")
        print(f"  Redacted: {result['redacted']}")
        print(f"  PII found: {result['pii_detected']} ({result['pii_count']} items)")

        if tc["expect_redacted"] is None:
            ok = result["pii_count"] == 0
        else:
            ok = tc["expect_redacted"] in result["redacted"]

        print(f"  Result: {'PASS' if ok else 'FAIL'}")
        if ok:
            passed += 1

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed}/{len(TEST_CASES)} tests passed")


if __name__ == "__main__":
    main()
