"""
Phase 3 — Confidence Scoring
Combines two signals:
1. Retrieval similarity  — how close are the retrieved policy chunks to the query?
2. Self-critique         — does the LLM think its own answer is grounded?
Final score is a weighted average (0.0 - 1.0).
"""

import os
import json
import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL   = os.getenv("LLM_MODEL",   "llama3.1:8b")

# Weights for final score
RETRIEVAL_WEIGHT  = 0.5
SELF_CRITIQUE_WEIGHT = 0.5

# Thresholds
CONFIDENCE_THRESHOLD_FALLBACK  = 0.6   # below this → route to Groq
CONFIDENCE_THRESHOLD_ESCALATE  = 0.4   # below this → force human escalation

SELF_CRITIQUE_PROMPT = """You are a quality control system for a fintech customer support AI.

Review the answer below and rate how confident you are that it is:
- Accurate and grounded in the policy context provided
- Complete enough to resolve the customer's question
- Free from hallucinations or unsupported claims

Policy context provided: {policy_context}
Customer question: {question}
Answer given: {answer}

Respond ONLY with valid JSON:
{{"confidence": <0.0-1.0>, "reason": "<one short sentence>"}}

Where 1.0 means fully grounded and accurate, 0.0 means completely unsupported."""


def score_retrieval(chunks: list[dict]) -> float:
    """
    Convert ChromaDB cosine distances to a confidence score.
    Distance 0.0 = perfect match → confidence 1.0
    Distance 1.0 = no match     → confidence 0.0
    We take the best (lowest) distance chunk as the primary signal.
    """
    if not chunks:
        return 0.0
    distances = [c["distance"] for c in chunks]
    best      = min(distances)
    # Convert distance to similarity score
    score = max(0.0, 1.0 - best)
    return round(score, 4)


def score_self_critique(
    question:       str,
    answer:         str,
    policy_context: str,
) -> dict:
    """
    Ask the local LLM to critique its own answer.
    Returns {"confidence": float, "reason": str}
    """
    prompt = SELF_CRITIQUE_PROMPT.format(
        policy_context = policy_context[:1500],  # keep prompt manageable
        question       = question,
        answer         = answer,
    )

    try:
        resp = requests.post(f"{OLLAMA_HOST}/api/generate", json={
            "model":  LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        })
        resp.raise_for_status()
        result = json.loads(resp.json()["response"])
        return {
            "confidence": float(result.get("confidence", 0.5)),
            "reason":     result.get("reason", ""),
        }
    except Exception as e:
        return {"confidence": 0.5, "reason": f"self-critique failed: {e}"}


def compute_confidence(
    chunks:         list[dict],
    question:       str,
    answer:         str,
    policy_context: str,
) -> dict:
    """
    Compute the final confidence score combining both signals.

    Returns:
    {
        "score":              float,   # 0.0 - 1.0 final score
        "retrieval_score":    float,
        "self_critique_score":float,
        "self_critique_reason": str,
        "needs_fallback":     bool,    # score < 0.6
        "needs_escalation":   bool,    # score < 0.4
    }
    """
    retrieval_score  = score_retrieval(chunks)
    critique         = score_self_critique(question, answer, policy_context)
    self_critique_score = critique["confidence"]

    final_score = round(
        (retrieval_score  * RETRIEVAL_WEIGHT) +
        (self_critique_score * SELF_CRITIQUE_WEIGHT),
        4
    )

    return {
        "score":                final_score,
        "retrieval_score":      retrieval_score,
        "self_critique_score":  self_critique_score,
        "self_critique_reason": critique["reason"],
        "needs_fallback":       final_score < CONFIDENCE_THRESHOLD_FALLBACK,
        "needs_escalation":     final_score < CONFIDENCE_THRESHOLD_ESCALATE,
    }
