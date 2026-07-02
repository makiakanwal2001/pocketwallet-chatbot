"""
Phase 1 — Agent Graph
Orchestrates the full pipeline:
language detection → sentiment → intent → retrieval → MCP tool call → answer generation
"""

import os
import json
import requests
from dataclasses import dataclass, field

from agent.language  import detect_language
from agent.sentiment import analyse_sentiment
from agent.intent    import detect_intent
from agent.retrieval import retrieve, format_citations
from mcp_servers.client import call_tool

OLLAMA_HOST   = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL     = os.getenv("LLM_MODEL",   "llama3.1:8b")
SESSION_TOKEN = "session_dev_001"   # hardcoded for Phase 1; JWT in Phase 5

# ── Intent → MCP tool mapping ─────────────────────────────────────────────────
INTENT_TOOL_MAP = {
    "card_freeze":      "freeze_card",
    "balance_inquiry":  "check_balance",
    "kyc_verification": "get_kyc_status",
    "dispute":          "get_transaction_history",
    "transfer":         None,   # policy-only answer
    "fee_inquiry":      None,   # policy-only answer
    "general":          None,
}

# ── Answer generation prompt ──────────────────────────────────────────────────
ANSWER_PROMPT = """You are a helpful, empathetic customer support agent for PocketWallet, a Pakistani fintech app.
Respond in {language}. If the customer wrote in Roman Urdu, respond in Roman Urdu.
Customer sentiment is {sentiment} — adjust your tone accordingly (more empathetic if frustrated/angry).

Use the policy context and tool result below to answer the customer accurately.
Always cite your source at the end using the format: Source: <doc_title>, <section>

Policy context:
{policy_context}

Tool result (live data):
{tool_result}

Customer message: {message}

Provide a clear, concise answer in 2-4 sentences. End with the source citation."""


# ── Agent state ───────────────────────────────────────────────────────────────
@dataclass
class AgentState:
    message:      str
    customer_id:  str
    language:     dict = field(default_factory=dict)
    sentiment:    dict = field(default_factory=dict)
    intent:       dict = field(default_factory=dict)
    policy_chunks:list = field(default_factory=list)
    tool_name:    str  = ""
    tool_result:  dict = field(default_factory=dict)
    answer:       str  = ""
    citations:    list = field(default_factory=list)


# ── Pipeline steps ────────────────────────────────────────────────────────────
def step_analyse(state: AgentState) -> AgentState:
    """Run language, sentiment, and intent detection in sequence."""
    state.language  = detect_language(state.message)
    state.sentiment = analyse_sentiment(state.message)
    state.intent    = detect_intent(state.message)
    return state


def step_retrieve(state: AgentState) -> AgentState:
    """Retrieve top-3 policy chunks for the customer message."""
    state.policy_chunks = retrieve(state.message, top_k=3)
    state.citations = [
        f"{c['doc_title']} > {c['section']} > {c['subsection']}"
        for c in state.policy_chunks
    ]
    return state


def step_tool_call(state: AgentState) -> AgentState:
    """Call the appropriate MCP tool based on detected intent."""
    intent     = state.intent.get("intent", "general")
    tool_name  = INTENT_TOOL_MAP.get(intent)

    if tool_name:
        state.tool_name   = tool_name
        state.tool_result = call_tool(tool_name, state.customer_id, SESSION_TOKEN)
    else:
        state.tool_name   = "none"
        state.tool_result = {}

    return state


def step_generate(state: AgentState) -> AgentState:
    """Generate the final customer-facing answer using Ollama."""
    lang_label  = state.language.get("language", "english")
    sent_label  = state.sentiment.get("sentiment", "neutral")
    policy_ctx  = format_citations(state.policy_chunks)
    tool_str    = json.dumps(state.tool_result, indent=2) if state.tool_result else "No live data retrieved."

    prompt = ANSWER_PROMPT.format(
        language       = lang_label,
        sentiment      = sent_label,
        policy_context = policy_ctx,
        tool_result    = tool_str,
        message        = state.message,
    )

    resp = requests.post(f"{OLLAMA_HOST}/api/generate", json={
        "model":  LLM_MODEL,
        "prompt": prompt,
        "stream": False,
    })
    resp.raise_for_status()
    state.answer = resp.json()["response"].strip()
    return state


# ── Main entry point ──────────────────────────────────────────────────────────
def run_agent(message: str, customer_id: str) -> dict:
    """
    Run the full agent pipeline and return a structured result.

    Returns:
    {
        "message":      str,
        "customer_id":  str,
        "language":     dict,
        "sentiment":    dict,
        "intent":       dict,
        "tool_called":  str,
        "tool_result":  dict,
        "citations":    list,
        "answer":       str,
    }
    """
    state = AgentState(message=message, customer_id=customer_id)
    state = step_analyse(state)
    state = step_retrieve(state)
    state = step_tool_call(state)
    state = step_generate(state)

    return {
        "message":     state.message,
        "customer_id": state.customer_id,
        "language":    state.language,
        "sentiment":   state.sentiment,
        "intent":      state.intent,
        "tool_called": state.tool_name,
        "tool_result": state.tool_result,
        "citations":   state.citations,
        "answer":      state.answer,
    }
