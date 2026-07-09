"""
Phase 7 — A/B Prompt Testing
Compares two prompt versions against the eval harness.
Runs each scenario through both prompts and picks the winner.
"""

import os
import json
import requests
import time
from datetime import datetime, timezone

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL   = os.getenv("LLM_MODEL",   "llama3.1:8b")

# ── Prompt versions ───────────────────────────────────────────────────────────
PROMPT_VERSIONS = {
    "v1": {
        "name":        "v1 — Formal",
        "description": "Formal, policy-first tone",
        "template": """You are a helpful customer support agent for PocketWallet, a Pakistani fintech app.
Use the policy context and tool result below to answer the customer accurately.
Always cite your source at the end using the format: Source: <doc_title>, <section>

Policy context:
{policy_context}

Tool result:
{tool_result}

Customer message: {message}

Provide a clear, concise answer in 2-4 sentences. End with the source citation."""
    },

    "v2": {
        "name":        "v2 — Empathetic",
        "description": "Warmer, customer-first tone with empathy",
        "template": """You are a warm, empathetic customer support agent for PocketWallet, a Pakistani fintech app.
The customer's sentiment is {sentiment}. Adjust your tone — be more empathetic if they are frustrated or angry.
Use the policy context and tool result below to answer accurately.
Always end with: Source: <doc_title>, <section>

Policy context:
{policy_context}

Tool result:
{tool_result}

Customer message: {message}

Respond warmly and clearly in 2-4 sentences. Acknowledge their concern if they seem upset."""
    },
}


def run_prompt(
    prompt_key:     str,
    message:        str,
    policy_context: str,
    tool_result:    str,
    sentiment:      str = "neutral",
) -> dict:
    """Run a single message through a specific prompt version."""
    template = PROMPT_VERSIONS[prompt_key]["template"]
    prompt   = template.format(
        message        = message,
        policy_context = policy_context,
        tool_result    = tool_result,
        sentiment      = sentiment,
    )

    start = time.time()
    resp  = requests.post(f"{OLLAMA_HOST}/api/generate", json={
        "model":  LLM_MODEL,
        "prompt": prompt,
        "stream": False,
    })
    resp.raise_for_status()
    elapsed = round(time.time() - start, 2)

    return {
        "prompt_version": prompt_key,
        "answer":         resp.json()["response"].strip(),
        "latency_secs":   elapsed,
    }


def compare_prompts(
    message:        str,
    policy_context: str,
    tool_result:    str = "No live data retrieved.",
    sentiment:      str = "neutral",
) -> dict:
    """
    Run the same message through both prompt versions.
    Returns both answers for side-by-side comparison.
    """
    results = {}
    for key in PROMPT_VERSIONS:
        results[key] = run_prompt(
            key, message, policy_context, tool_result, sentiment
        )

    return {
        "message":   message,
        "sentiment": sentiment,
        "results":   results,
    }


def run_ab_test(test_messages: list[dict]) -> dict:
    """
    Run A/B test across multiple messages.
    Each message dict: {message, policy_context, tool_result, sentiment}
    """
    print("\n" + "=" * 65)
    print("Phase 7 — A/B Prompt Comparison")
    print(f"Testing {len(test_messages)} messages across {len(PROMPT_VERSIONS)} prompt versions")
    print("=" * 65)

    all_results  = []
    latency_sums = {k: 0.0 for k in PROMPT_VERSIONS}

    for i, item in enumerate(test_messages, 1):
        print(f"\n[{i}/{len(test_messages)}] {item['message'][:60]}...")
        comparison = compare_prompts(
            message        = item["message"],
            policy_context = item.get("policy_context", "No policy context."),
            tool_result    = item.get("tool_result", "No live data."),
            sentiment      = item.get("sentiment", "neutral"),
        )
        all_results.append(comparison)

        for key, res in comparison["results"].items():
            latency_sums[key] += res["latency_secs"]
            print(f"\n  [{PROMPT_VERSIONS[key]['name']}] ({res['latency_secs']}s)")
            print(f"  {res['answer'][:150]}...")

    # Summary
    avg_latency = {k: round(latency_sums[k] / len(test_messages), 2)
                   for k in PROMPT_VERSIONS}

    print(f"\n{'=' * 65}")
    print("A/B Test Summary")
    for key, name_data in PROMPT_VERSIONS.items():
        print(f"  {name_data['name']}: avg latency={avg_latency[key]}s")
    print("=" * 65)

    return {
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "results":     all_results,
        "avg_latency": avg_latency,
    }
