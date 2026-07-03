"""
Phase 3 — Confidence Scoring & Escalation Test Scenarios
6 scenarios covering: forced escalation, low confidence, fallback routing.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.language   import detect_language
from agent.sentiment  import analyse_sentiment
from agent.intent     import detect_intent
from agent.retrieval  import retrieve, format_citations
from agent.confidence import compute_confidence
from agent.escalation import check_forced_escalation, build_escalation_package, call_groq_fallback
from agent.graph      import run_agent
from security.pii_redaction import redact

DIVIDER = "=" * 65

SCENARIOS = [
    {
        "id":          1,
        "description": "Legal threat — forced escalation regardless of confidence",
        "customer_id": "cust_001",
        "message":     "I am going to take legal action and file a court order against PocketWallet!",
        "expect_escalation": True,
        "expect_reason":     "legal",
    },
    {
        "id":          2,
        "description": "Fraud report — forced escalation",
        "customer_id": "cust_003",
        "message":     "My account has been hacked and there is unauthorized access. This is fraud!",
        "expect_escalation": True,
        "expect_reason":     "fraud",
    },
    {
        "id":          3,
        "description": "Account closure — forced escalation",
        "customer_id": "cust_001",
        "message":     "I want to close my account permanently. Please delete everything.",
        "expect_escalation": True,
        "expect_reason":     "account closure",
    },
    {
        "id":          4,
        "description": "PII in message — redacted before LLM",
        "customer_id": "cust_002",
        "message":     "My CNIC is 42101-1234567-8 and my card is 4111111111111111, please help with KYC.",
        "expect_escalation": False,
        "expect_pii_redacted": True,
    },
    {
        "id":          5,
        "description": "Angry frustrated customer — sentiment escalation signal",
        "customer_id": "cust_002",
        "message":     "I have called you 5 times already! Nobody is helping me! This is the worst service ever!",
        "expect_escalation": False,
        "expect_sentiment":  "angry",
    },
    {
        "id":          6,
        "description": "SBP regulatory complaint — forced escalation",
        "customer_id": "cust_003",
        "message":     "I am going to file an SBP complaint and contact the mohtasib about this issue.",
        "expect_escalation": True,
        "expect_reason":     "regulatory",
    },
]


def run_scenario(scenario: dict) -> bool:
    print(f"\n{DIVIDER}")
    print(f"Scenario #{scenario['id']}: {scenario['description']}")
    print(f"Customer: {scenario['customer_id']}")
    print(f"Message:  {scenario['message']}")
    print("-" * 65)

    passed = True

    try:
        # Step 1 — PII Redaction
        redaction    = redact(scenario["message"])
        safe_message = redaction["redacted"]
        if redaction["pii_count"] > 0:
            print(f"[PII]       {redaction['pii_count']} items redacted: {redaction['pii_detected']}")
            print(f"            Safe: {safe_message}")
        else:
            print(f"[PII]       No PII detected")

        # Step 2 — Forced escalation check (on original message)
        forced = check_forced_escalation(scenario["message"])
        print(f"[Escalation] forced={forced['should_escalate']} | "
              f"reason={forced['reason'] or 'none'} | "
              f"keywords={forced['matched_keywords']}")

        # Step 3 — Core analysis on safe (redacted) message
        lang       = detect_language(safe_message)
        sent       = analyse_sentiment(safe_message)
        intent     = detect_intent(safe_message)
        chunks     = retrieve(safe_message, top_k=3)
        policy_ctx = format_citations(chunks)

        print(f"[Language]  {lang['language']} (conf: {lang['confidence']:.2f})")
        print(f"[Sentiment] {sent['sentiment']} (conf: {sent['confidence']:.2f})")
        print(f"[Intent]    {intent['intent']} (conf: {intent['confidence']:.2f})")
        print(f"[Retrieval] {len(chunks)} chunks retrieved")

        # Step 4 — Generate draft answer
        result       = run_agent(safe_message, scenario["customer_id"])
        draft_answer = result["answer"]

        # Step 5 — Confidence scoring
        confidence = compute_confidence(chunks, safe_message, draft_answer, policy_ctx)
        print(f"[Confidence] score={confidence['score']:.2f} | "
              f"retrieval={confidence['retrieval_score']:.2f} | "
              f"self_critique={confidence['self_critique_score']:.2f}")
        print(f"             needs_fallback={confidence['needs_fallback']} | "
              f"needs_escalation={confidence['needs_escalation']}")

        # Step 6 — Fallback routing if needed
        if confidence["needs_fallback"] and not forced["should_escalate"]:
            print(f"[Fallback]  Routing to Groq (confidence={confidence['score']:.2f} < 0.6)")
            fallback = call_groq_fallback(safe_message, policy_ctx)
            print(f"            success={fallback['success']} | model={fallback['model']}")

        # Step 7 — Build escalation package if needed
        if forced["should_escalate"]:
            pkg = build_escalation_package(
                conversation_id   = f"conv_{scenario['customer_id']}",
                customer_id       = scenario["customer_id"],
                message           = safe_message,
                sentiment         = sent,
                intent            = intent,
                confidence        = confidence,
                answer            = draft_answer,
                escalation_reason = forced["reason"],
            )
            print(f"[Package]   priority={pkg['priority']} | "
                  f"id={pkg['escalation_id']}")
            print(f"            action={pkg['recommended_action']}")

        # ── Checks ────────────────────────────────────────────────────────────
        print("\n[Checks]")
        checks = []

        if "expect_escalation" in scenario:
            ok = forced["should_escalate"] == scenario["expect_escalation"]
            checks.append(("escalation correct", ok))

        if "expect_reason" in scenario:
            ok = scenario["expect_reason"] in forced["reason"].lower()
            checks.append(("escalation reason correct", ok))

        if scenario.get("expect_pii_redacted"):
            ok = redaction["pii_count"] > 0
            checks.append(("PII was redacted", ok))

        if "expect_sentiment" in scenario:
            ok = sent["sentiment"] == scenario["expect_sentiment"]
            checks.append(("sentiment correct", ok))

        for label, ok in checks:
            status = "OK" if ok else "FAIL"
            print(f"  [{status}] {label}")
            if not ok:
                passed = False

        print(f"\n  -> {'PASS' if passed else 'FAIL'}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        passed = False

    return passed


def main():
    print(DIVIDER)
    print("PocketWallet — Phase 3 Escalation & Confidence Scenarios")
    print(f"Running {len(SCENARIOS)} scenarios")
    print(DIVIDER)

    results = [run_scenario(s) for s in SCENARIOS]
    passed  = sum(results)
    total   = len(results)

    print(f"\n{DIVIDER}")
    print(f"RESULTS: {passed}/{total} scenarios passed")
    dod_met = passed == total
    print(f"Phase 3 DoD: {'MET' if dod_met else 'NOT MET'}")
    print(DIVIDER)


if __name__ == "__main__":
    main()