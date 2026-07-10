"""
Phase 9/10 — Updated Agent Graph
Wires growth events into the agent pipeline automatically.
Events fire based on intent, tool results, and escalation outcomes.
"""

import os
import json
import requests
from dataclasses import dataclass, field

from agent.language   import detect_language
from agent.sentiment  import analyse_sentiment
from agent.intent     import detect_intent
from agent.retrieval  import retrieve, format_citations
from agent.confidence import compute_confidence
from agent.escalation import check_forced_escalation, build_escalation_package
from mcp_servers.client import call_tool
from growth.events    import (publish_event, event_card_blocked,
                               event_dispute_opened, event_kyc_incomplete,
                               EVENT_ESCALATION)

OLLAMA_HOST   = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL     = os.getenv("LLM_MODEL",   "llama3.1:8b")
SESSION_TOKEN = "session_dev_001"

INTENT_TOOL_MAP = {
    "card_freeze":      "freeze_card",
    "balance_inquiry":  "check_balance",
    "kyc_verification": "get_kyc_status",
    "dispute":          "get_transaction_history",
    "transfer":         None,
    "fee_inquiry":      None,
    "general":          None,
}

ANSWER_PROMPT = """You are a helpful, empathetic customer support agent for PocketWallet, a Pakistani fintech app.
Respond in {language}. If the customer wrote in Roman Urdu, respond in Roman Urdu.
Customer sentiment is {sentiment} — adjust your tone accordingly.

Use the policy context and tool result below to answer the customer accurately.
Always cite your source at the end: Source: <doc_title>, <section>

Policy context:
{policy_context}

Tool result:
{tool_result}

Customer message: {message}

Provide a clear, concise answer in 2-4 sentences. End with the source citation."""


@dataclass
class AgentState:
    message:        str
    customer_id:    str
    conversation_id:str = ""
    language:       dict = field(default_factory=dict)
    sentiment:      dict = field(default_factory=dict)
    intent:         dict = field(default_factory=dict)
    policy_chunks:  list = field(default_factory=list)
    tool_name:      str  = ""
    tool_result:    dict = field(default_factory=dict)
    confidence:     dict = field(default_factory=dict)
    escalation:     dict = field(default_factory=dict)
    answer:         str  = ""
    citations:      list = field(default_factory=list)
    events_fired:   list = field(default_factory=list)


def _fire_growth_events(state: AgentState):
    """Fire Redis growth events based on agent outcomes."""
    intent     = state.intent.get("intent", "general")
    tool_result= state.tool_result
    customer_id= state.customer_id

    # Card freeze → fire card_blocked event
    if intent == "card_freeze" and tool_result.get("result") == "success":
        event_card_blocked(customer_id, reason="customer_request")
        state.events_fired.append("card_blocked")

    # Dispute → fire dispute_opened event
    if intent == "dispute" and not tool_result.get("error"):
        event_dispute_opened(customer_id, dispute_type="customer_reported")
        state.events_fired.append("dispute_opened")

    # KYC pending → fire kyc_incomplete event
    if intent == "kyc_verification":
        kyc_status = tool_result.get("kyc_status", "")
        if kyc_status == "pending":
            pending_docs = tool_result.get("pending_docs", [])
            event_kyc_incomplete(customer_id, missing_docs=pending_docs)
            state.events_fired.append("kyc_incomplete")

    # Escalation → fire escalation event
    if state.escalation.get("should_escalate"):
        publish_event(EVENT_ESCALATION, customer_id, {
            "reason":          state.escalation.get("reason", ""),
            "conversation_id": state.conversation_id,
            "sentiment":       state.sentiment.get("sentiment", ""),
        })
        state.events_fired.append("escalation")


def run_agent_v2(message: str, customer_id: str,
                 conversation_id: str = "") -> dict:
    """
    Full agent pipeline with growth event integration.
    Identical to run_agent() but fires Redis events automatically.
    """
    state = AgentState(
        message         = message,
        customer_id     = customer_id,
        conversation_id = conversation_id or f"conv_{customer_id}",
    )

    # 1. Analyse
    state.language  = detect_language(message)
    state.sentiment = analyse_sentiment(message)
    state.intent    = detect_intent(message)

    # 2. Retrieve
    state.policy_chunks = retrieve(message, top_k=3)
    state.citations = [
        f"{c['doc_title']} > {c['section']} > {c['subsection']}"
        for c in state.policy_chunks
    ]
    policy_ctx = format_citations(state.policy_chunks)

    # 3. Escalation check
    state.escalation = check_forced_escalation(message)

    # 4. Tool call
    tool_name = INTENT_TOOL_MAP.get(state.intent.get("intent", "general"))
    if tool_name:
        state.tool_name   = tool_name
        state.tool_result = call_tool(tool_name, customer_id, SESSION_TOKEN)
    else:
        state.tool_name = "none"

    # 5. Generate answer
    tool_str = json.dumps(state.tool_result, indent=2) if state.tool_result else "No live data."
    prompt   = ANSWER_PROMPT.format(
        language       = state.language.get("language", "english"),
        sentiment      = state.sentiment.get("sentiment", "neutral"),
        policy_context = policy_ctx,
        tool_result    = tool_str,
        message        = message,
    )
    resp = requests.post(f"{OLLAMA_HOST}/api/generate", json={
        "model":  LLM_MODEL,
        "prompt": prompt,
        "stream": False,
    })
    resp.raise_for_status()
    state.answer = resp.json()["response"].strip()

    # 6. Confidence scoring
    state.confidence = compute_confidence(
        state.policy_chunks, message, state.answer, policy_ctx
    )

    # 7. Fire growth events
    _fire_growth_events(state)

    return {
        "message":       state.message,
        "customer_id":   state.customer_id,
        "language":      state.language,
        "sentiment":     state.sentiment,
        "intent":        state.intent,
        "tool_called":   state.tool_name,
        "tool_result":   state.tool_result,
        "citations":     state.citations,
        "confidence":    state.confidence,
        "escalation":    state.escalation,
        "answer":        state.answer,
        "events_fired":  state.events_fired,
    }
