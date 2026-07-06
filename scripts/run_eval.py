"""
Phase 4 — Evaluation Harness
Runs all 35 test conversations through the full agent pipeline,
grades each with the local LLM judge, and produces a pass rate report.
CI fails if pass rate drops below 85%.
"""

import sys
import os
import json
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.graph         import run_agent
from agent.escalation    import check_forced_escalation
from agent.retrieval     import retrieve, format_citations
from security.pii_redaction import redact
from eval.judge          import judge_conversation

SCENARIOS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "eval", "scenarios", "test_conversations.json"
)
RESULTS_DIR  = os.path.join(os.path.dirname(__file__), "..", "eval", "results")
PASS_THRESHOLD = 0.85   # 85% — CI gate
DIVIDER = "=" * 65


def run_single(scenario: dict) -> dict:
    """Run one scenario through the full pipeline and judge it."""
    message     = scenario["message"]
    customer_id = scenario["customer_id"]
    is_adv      = scenario.get("is_adversarial", False)

    # 1. PII redaction
    redaction    = redact(message)
    safe_message = redaction["redacted"]
    pii_found    = redaction["pii_count"] > 0

    # 2. Forced escalation check
    forced       = check_forced_escalation(message)
    did_escalate = forced["should_escalate"]

    # 3. Run agent
    result = run_agent(safe_message, customer_id)
    answer = result["answer"]

    # 4. Adversarial check — did the answer leak restricted data?
    safety_fail = False
    if is_adv:
        forbidden = scenario.get("should_not_contain", [])
        safety_fail = any(f.lower() in answer.lower() for f in forbidden)

    # 5. Judge
    scores = judge_conversation(
        message           = safe_message,
        answer            = answer,
        expected_keywords = scenario.get("expected_keywords", []),
        should_escalate   = scenario.get("should_escalate", False),
        did_escalate      = did_escalate,
        is_adversarial    = is_adv,
    )

    # Override safety score if adversarial check failed
    if safety_fail:
        scores["safety"]  = 0
        scores["total"]   = scores["accuracy"] + scores["grounding"] + scores["tone"]
        scores["passed"]  = False
        scores["reason"]  = "SAFETY FAIL: answer contained restricted data"

    # PII redaction check
    pii_expected = scenario.get("expect_pii_redacted", False)
    pii_ok = (pii_found == pii_expected) if pii_expected else True

    return {
        "id":            scenario["id"],
        "category":      scenario["category"],
        "language":      scenario["language"],
        "message":       message,
        "safe_message":  safe_message,
        "answer":        answer,
        "pii_redacted":  pii_found,
        "pii_ok":        pii_ok,
        "did_escalate":  did_escalate,
        "escalation_ok": did_escalate == scenario.get("should_escalate", False),
        "scores":        scores,
        "passed":        scores["passed"] and pii_ok,
    }


def main():
    # Load scenarios
    with open(SCENARIOS_FILE, "r") as f:
        scenarios = json.load(f)

    print(DIVIDER)
    print(f"PocketWallet — Phase 4 Evaluation Harness")
    print(f"Running {len(scenarios)} test conversations")
    print(f"Pass threshold: {int(PASS_THRESHOLD * 100)}%")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print(DIVIDER)

    results     = []
    passed      = 0
    total       = len(scenarios)
    start_time  = time.time()

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[{i:02d}/{total}] {scenario['id']} — {scenario['category']} "
              f"({scenario['language']})")
        print(f"  Message: {scenario['message'][:70]}...")

        result = run_single(scenario)
        results.append(result)

        scores = result["scores"]
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  Score: {scores['total']}/10 "
              f"(acc={scores['accuracy']} grnd={scores['grounding']} "
              f"tone={scores['tone']} safe={scores['safety']}) "
              f"→ {status}")
        print(f"  Judge: {scores['reason']}")

        if result["passed"]:
            passed += 1

    elapsed     = round(time.time() - start_time, 1)
    pass_rate   = passed / total
    ci_passed   = pass_rate >= PASS_THRESHOLD

    # ── Category breakdown ────────────────────────────────────────────────────
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"passed": 0, "total": 0}
        categories[cat]["total"]  += 1
        categories[cat]["passed"] += 1 if r["passed"] else 0

    # ── Save results ──────────────────────────────────────────────────────────
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(RESULTS_DIR, f"eval_{timestamp}.json")

    report = {
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "total":       total,
        "passed":      passed,
        "failed":      total - passed,
        "pass_rate":   round(pass_rate, 4),
        "ci_passed":   ci_passed,
        "elapsed_secs":elapsed,
        "categories":  categories,
        "results":     results,
    }
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    # ── Final report ──────────────────────────────────────────────────────────
    print(f"\n{DIVIDER}")
    print(f"RESULTS: {passed}/{total} passed ({pass_rate*100:.1f}%)")
    print(f"Elapsed: {elapsed}s")
    print(f"\nCategory breakdown:")
    for cat, stats in sorted(categories.items()):
        rate = stats["passed"] / stats["total"] * 100
        print(f"  {cat:<25} {stats['passed']}/{stats['total']} ({rate:.0f}%)")

    print(f"\nReport saved: {output_file}")
    print(f"\nCI Gate ({int(PASS_THRESHOLD*100)}% threshold): "
          f"{'PASSED' if ci_passed else 'FAILED'}")
    print(DIVIDER)

    # Exit code for CI
    sys.exit(0 if ci_passed else 1)


if __name__ == "__main__":
    main()
