"""
Phase 1 — 7 CLI Test Scenarios
5 English + 2 Roman Urdu
DoD: all run end-to-end, produce policy-grounded answers with citations,
     and at least 2 trigger MCP tool calls.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.graph import run_agent

DIVIDER = "=" * 65

# ── 7 Test scenarios ──────────────────────────────────────────────────────────
SCENARIOS = [
    # ── English scenarios ─────────────────────────────────────────────────────
    {
        "id":          1,
        "lang":        "English",
        "customer_id": "cust_001",
        "message":     "My card was stolen, please block it immediately!",
        "expect_intent": "card_freeze",
        "expect_tool":   "freeze_card",
    },
    {
        "id":          2,
        "lang":        "English",
        "customer_id": "cust_001",
        "message":     "What is the fee for sending money to another bank account?",
        "expect_intent": "fee_inquiry",
        "expect_tool":   "none",
    },
    {
        "id":          3,
        "lang":        "English",
        "customer_id": "cust_003",
        "message":     "I want to dispute a transaction. There is a charge I did not make.",
        "expect_intent": "dispute",
        "expect_tool":   "get_transaction_history",
    },
    {
        "id":          4,
        "lang":        "English",
        "customer_id": "cust_002",
        "message":     "Why can I not send money? What is my KYC status?",
        "expect_intent": "kyc_verification",
        "expect_tool":   "get_kyc_status",
    },
    {
        "id":          5,
        "lang":        "English",
        "customer_id": "cust_001",
        "message":     "What is my current balance?",
        "expect_intent": "balance_inquiry",
        "expect_tool":   "check_balance",
    },
    # ── Roman Urdu scenarios ──────────────────────────────────────────────────
    {
        "id":          6,
        "lang":        "Roman Urdu",
        "customer_id": "cust_002",
        "message":     "Mera card block kar do, kho gaya hai",
        "expect_intent": "card_freeze",
        "expect_tool":   "freeze_card",
    },
    {
        "id":          7,
        "lang":        "Roman Urdu",
        "customer_id": "cust_001",
        "message":     "Mera balance kitna hai abhi?",
        "expect_intent": "balance_inquiry",
        "expect_tool":   "check_balance",
    },
]


# ── Runner ────────────────────────────────────────────────────────────────────
def run_scenario(scenario: dict) -> bool:
    print(f"\n{DIVIDER}")
    print(f"Scenario #{scenario['id']} [{scenario['lang']}] — Customer: {scenario['customer_id']}")
    print(f"Message: {scenario['message']}")
    print("-" * 65)

    try:
        result = run_agent(scenario["message"], scenario["customer_id"])

        # ── Analysis results ──────────────────────────────────────────────────
        lang = result["language"]
        sent = result["sentiment"]
        intent = result["intent"]

        print(f"[Language]  {lang['language']} (conf: {lang['confidence']:.2f})")
        print(f"[Sentiment] {sent['sentiment']} (conf: {sent['confidence']:.2f})")
        print(f"[Intent]    {intent['intent']} (conf: {intent['confidence']:.2f})")

        # ── Tool call ─────────────────────────────────────────────────────────
        tool_called = result["tool_called"]
        if tool_called and tool_called != "none":
            tool_res = result["tool_result"]
            if "error" in tool_res:
                print(f"[Tool]      {tool_called} → ERROR: {tool_res['error']}")
            else:
                print(f"[Tool]      {tool_called} → OK")
        else:
            print(f"[Tool]      none (policy-only answer)")

        # ── Citations ─────────────────────────────────────────────────────────
        print(f"[Citations] {len(result['citations'])} sources retrieved:")
        for c in result["citations"]:
            print(f"  • {c}")

        # ── Answer ────────────────────────────────────────────────────────────
        print(f"\n[Answer]\n{result['answer']}")

        # ── Pass/Fail check ───────────────────────────────────────────────────
        intent_ok = intent["intent"] == scenario["expect_intent"]
        tool_ok   = tool_called == scenario["expect_tool"]
        cite_ok   = len(result["citations"]) > 0
        answer_ok = len(result["answer"]) > 20

        passed = intent_ok and cite_ok and answer_ok
        status = "PASS" if passed else "FAIL"

        print(f"\n[Check] intent={'OK' if intent_ok else 'MISMATCH'} | "
              f"tool={'OK' if tool_ok else 'MISMATCH'} | "
              f"citations={'OK' if cite_ok else 'MISSING'} | "
              f"answer={'OK' if answer_ok else 'EMPTY'} → {status}")

        return passed

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print(DIVIDER)
    print("PocketWallet — Phase 1 CLI Test Scenarios")
    print(f"Running {len(SCENARIOS)} scenarios (5 English + 2 Roman Urdu)")
    print(DIVIDER)

    results  = [run_scenario(s) for s in SCENARIOS]
    passed   = sum(results)
    total    = len(results)
    tool_scenarios = [s for s in SCENARIOS if s["expect_tool"] != "none"]
    tools_triggered = sum(
        1 for s, r in zip(SCENARIOS, results)
        if r and s["expect_tool"] != "none"
    )

    print(f"\n{DIVIDER}")
    print(f"RESULTS: {passed}/{total} scenarios passed")
    print(f"MCP tool calls triggered: {tools_triggered}/{len(tool_scenarios)}")

    dod_met = passed == total and tools_triggered >= 2
    print(f"Phase 1 DoD: {'MET ✓' if dod_met else 'NOT MET ✗'}")
    print(DIVIDER)


if __name__ == "__main__":
    main()
