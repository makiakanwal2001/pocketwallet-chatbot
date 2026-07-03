"""
Phase 2 — MCP Scope Test
Verifies that out-of-scope tool calls are blocked
and in-scope calls are allowed.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from security.mcp_scope import create_scope, get_scope, clear_scope

DIVIDER = "-" * 60

TEST_CASES = [
    {
        "id":          1,
        "description": "Standard customer CAN check balance (account server)",
        "profile":     "customer_standard",
        "tool":        "check_balance",
        "expect":      True,
    },
    {
        "id":          2,
        "description": "Standard customer CAN freeze card (card server)",
        "profile":     "customer_standard",
        "tool":        "freeze_card",
        "expect":      True,
    },
    {
        "id":          3,
        "description": "Standard customer CANNOT access CRM history (crm server)",
        "profile":     "customer_standard",
        "tool":        "get_customer_history",
        "expect":      False,
    },
    {
        "id":          4,
        "description": "Standard customer CANNOT run AML check (compliance server)",
        "profile":     "customer_standard",
        "tool":        "kyc_aml_check",
        "expect":      False,
    },
    {
        "id":          5,
        "description": "Agent CAN access CRM history (crm server)",
        "profile":     "agent_support",
        "tool":        "get_customer_history",
        "expect":      True,
    },
    {
        "id":          6,
        "description": "Agent CAN run AML check (compliance server)",
        "profile":     "agent_support",
        "tool":        "kyc_aml_check",
        "expect":      True,
    },
    {
        "id":          7,
        "description": "Unknown tool is always blocked",
        "profile":     "admin",
        "tool":        "delete_all_users",
        "expect":      False,
    },
]


def main():
    print("Phase 2 — MCP Scope Tests")
    print("=" * 60)

    passed = 0
    for tc in TEST_CASES:
        conv_id = f"conv_test_{tc['id']}"
        scope   = create_scope(conv_id, "cust_test", tc["profile"])
        result  = scope.check(tc["tool"])

        ok = result["allowed"] == tc["expect"]
        status = "PASS" if ok else "FAIL"

        print(f"\nTest #{tc['id']}: {tc['description']}")
        print(f"  Profile: {tc['profile']} | Tool: {tc['tool']}")
        print(f"  Allowed: {result['allowed']} | Reason: {result['reason']}")
        print(f"  Result: {status}")

        if ok:
            passed += 1

        clear_scope(conv_id)

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed}/{len(TEST_CASES)} tests passed")


if __name__ == "__main__":
    main()
