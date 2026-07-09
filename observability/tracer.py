"""
Phase 7 — Langfuse Tracing
Compatible with Langfuse SDK v4+
"""

import os
from langfuse import Langfuse

_client = None

def get_langfuse() -> Langfuse:
    global _client
    if _client is None:
        _client = Langfuse(
            public_key = os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            secret_key = os.getenv("LANGFUSE_SECRET_KEY", ""),
            host       = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    return _client


def trace_agent_run(
    conversation_id: str,
    customer_id:     str,
    message:         str,
    result:          dict,
    confidence:      dict = None,
    escalated:       bool = False,
) -> str:
    """
    Send a completed agent run to Langfuse v4.
    Returns the trace ID.
    """
    lf = get_langfuse()

    with lf.start_as_current_observation(
        name  = "agent_pipeline",
        input = {"message": message},
    ) as observation:

        lf.set_current_trace_io(
            input  = {"message": message},
            output = {
                "answer":      result.get("answer", ""),
                "intent":      result.get("intent", {}).get("intent", ""),
                "sentiment":   result.get("sentiment", {}).get("sentiment", ""),
                "tool_called": result.get("tool_called", "none"),
                "citations":   result.get("citations", []),
                "escalated":   escalated,
            },
        )

        lf.update_current_span(
            metadata = {
                "conversation_id": conversation_id,
                "customer_id":     customer_id,
                "language":        result.get("language", {}).get("language", ""),
                "confidence":      confidence or {},
            },
        )

        if confidence:
            lf.score_current_trace(
                name    = "confidence",
                value   = float(confidence.get("score", 0.0)),
                comment = confidence.get("self_critique_reason", ""),
            )

        trace_id = lf.get_current_trace_id()

    lf.flush()
    print(f"[Langfuse] trace_id={trace_id}")
    return trace_id or "unknown"
