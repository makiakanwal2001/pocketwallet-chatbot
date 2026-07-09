"""
Phase 7 — Observability & Quality Scoring Tests
Tests: Langfuse tracing, drift detection, A/B prompt comparison.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from observability.tracer        import trace_agent_run, get_langfuse
from observability.drift_detector import detect_drift, print_drift_report
from observability.ab_testing    import run_ab_test, compare_prompts
from agent.graph                 import run_agent

DIVIDER = "=" * 65


def test_langfuse_tracing():
    print(f"\n{DIVIDER}")
    print("Test 1: Langfuse Tracing")
    print(DIVIDER)

    try:
        # Run a real agent call and trace it
        message     = "What is the fee for IBFT transfers?"
        customer_id = "cust_001"
        result      = run_agent(message, customer_id)

        trace_id = trace_agent_run(
            conversation_id = "conv_phase7_test_001",
            customer_id     = customer_id,
            message         = message,
            result          = result,
            confidence      = {"score": 0.82, "self_critique_reason": "well grounded"},
            escalated       = False,
        )

        print(f"  [PASS] Trace sent to Langfuse")
        print(f"  Trace ID: {trace_id}")
        print(f"  Intent:   {result['intent']['intent']}")
        print(f"  Answer:   {result['answer'][:100]}...")
        print(f"  View at:  https://cloud.langfuse.com")
        return True

    except Exception as e:
        print(f"  [FAIL] Langfuse tracing error: {e}")
        return False


def test_drift_detection():
    print(f"\n{DIVIDER}")
    print("Test 2: Drift Detection")
    print(DIVIDER)

    try:
        print_drift_report()
        report = detect_drift()

        if report["baseline_rate"] is None:
            print("  [INFO] Only one eval run found — need 2+ for drift comparison")
            print("  [PASS] Drift detector loaded and ran without errors")
        else:
            print(f"\n  [PASS] Drift detection complete")
            print(f"  has_drift={report['has_drift']} | delta={report['delta']*100:+.1f}%")

        return True

    except Exception as e:
        print(f"  [FAIL] Drift detection error: {e}")
        return False


def test_ab_comparison():
    print(f"\n{DIVIDER}")
    print("Test 3: A/B Prompt Comparison")
    print(DIVIDER)

    test_messages = [
        {
            "message":        "What is the IBFT transfer fee?",
            "policy_context": "Section 1.1 Standard Transfer: IBFT transfers cost PKR 15 per transaction. First 3 per month are free.",
            "tool_result":    "No live data.",
            "sentiment":      "neutral",
        },
        {
            "message":        "I have been waiting for 3 days and nobody is helping me!",
            "policy_context": "Section 3.1 Standard Timelines: Disputes resolved in 5-10 business days.",
            "tool_result":    "No live data.",
            "sentiment":      "angry",
        },
    ]

    try:
        results = run_ab_test(test_messages)
        print(f"\n  [PASS] A/B test complete — {len(results['results'])} comparisons run")
        return True

    except Exception as e:
        print(f"  [FAIL] A/B test error: {e}")
        return False


def main():
    print(DIVIDER)
    print("PocketWallet — Phase 7 Observability Tests")
    print(DIVIDER)

    results = [
        test_langfuse_tracing(),
        test_drift_detection(),
        test_ab_comparison(),
    ]

    passed = sum(results)
    total  = len(results)

    print(f"\n{DIVIDER}")
    print(f"RESULTS: {passed}/{total} tests passed")
    print(f"Phase 7 DoD: {'MET ✓' if passed == total else 'NOT MET ✗'}")
    print(DIVIDER)


if __name__ == "__main__":
    main()
