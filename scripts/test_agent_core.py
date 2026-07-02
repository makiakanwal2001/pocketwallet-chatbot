"""
Phase 1 — Agent Core Smoke Test
Tests language detection, sentiment analysis, intent detection,
and policy retrieval against sample messages.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.language  import detect_language
from agent.sentiment import analyse_sentiment
from agent.intent    import detect_intent
from agent.retrieval import retrieve, format_citations

# ── Test messages ─────────────────────────────────────────────────────────────
TEST_MESSAGES = [
    {
        "id":  1,
        "msg": "My card was stolen, please block it immediately!",
        "lang": "english"
    },
    {
        "id":  2,
        "msg": "What is the fee for sending money to another bank?",
        "lang": "english"
    },
    {
        "id":  3,
        "msg": "Mera balance check karna hai",   # Roman Urdu: "I want to check my balance"
        "lang": "roman_urdu"
    },
]

DIVIDER = "-" * 60

def test_message(item: dict):
    msg = item["msg"]
    print(f"\n{'=' * 60}")
    print(f"Message #{item['id']}: {msg}")
    print(DIVIDER)

    # 1. Language
    lang = detect_language(msg)
    status = "OK" if lang["language"] == item["lang"] else "MISMATCH"
    print(f"[Language]  {lang['language']} "
          f"(conf: {lang['confidence']:.2f}) [{status}]")

    # 2. Sentiment
    sent = analyse_sentiment(msg)
    print(f"[Sentiment] {sent['sentiment']} "
          f"(conf: {sent['confidence']:.2f}) — {sent['reason']}")

    # 3. Intent
    intent = detect_intent(msg)
    print(f"[Intent]    {intent['intent']} "
          f"(conf: {intent['confidence']:.2f}) — {intent['reason']}")

    # 4. Retrieval
    chunks = retrieve(msg, top_k=2)
    print(f"[Retrieval] {len(chunks)} chunks retrieved:")
    for chunk in chunks:
        print(f"  • {chunk['doc_title']} > {chunk['subsection']} "
              f"(dist: {chunk['distance']})")


def main():
    print("PocketWallet Agent Core — Smoke Test")
    print("=" * 60)

    passed = 0
    for item in TEST_MESSAGES:
        try:
            test_message(item)
            passed += 1
        except Exception as e:
            print(f"\nERROR on message #{item['id']}: {e}")

    print(f"\n{'=' * 60}")
    print(f"Completed: {passed}/{len(TEST_MESSAGES)} messages processed")


if __name__ == "__main__":
    main()
