"""
Phase 1 — Sentiment Analysis
Detects customer sentiment to adjust tone and priority.
Uses Ollama LLM with a structured prompt returning JSON.
"""

import os
import json
import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL   = os.getenv("LLM_MODEL", "llama3.1:8b")

SENTIMENT_LABELS = ["positive", "neutral", "frustrated", "angry"]

PROMPT = """You are a sentiment analysis system for a Pakistani fintech customer support app.
Analyse the sentiment of the customer message below.

Sentiment labels:
- "positive": customer is happy, satisfied, or making a simple request politely
- "neutral": customer is asking a factual question with no strong emotion
- "frustrated": customer is unhappy, has contacted support multiple times, or is losing patience
- "angry": customer is very upset, using strong language, or making threats

Respond ONLY with valid JSON in this exact format:
{{"sentiment": "<positive|neutral|frustrated|angry>", "confidence": <0.0-1.0>, "reason": "<one short sentence>"}}

Customer message: {message}"""


def analyse_sentiment(message: str) -> dict:
    """
    Returns: {
        "sentiment":  "positive" | "neutral" | "frustrated" | "angry",
        "confidence": float,
        "reason":     str
    }
    """
    resp = requests.post(f"{OLLAMA_HOST}/api/generate", json={
        "model":  LLM_MODEL,
        "prompt": PROMPT.format(message=message),
        "stream": False,
        "format": "json"
    })
    resp.raise_for_status()

    raw    = resp.json()["response"]
    result = json.loads(raw)

    sentiment = result.get("sentiment", "neutral").lower()
    if sentiment not in SENTIMENT_LABELS:
        sentiment = "neutral"

    return {
        "sentiment":  sentiment,
        "confidence": float(result.get("confidence", 0.8)),
        "reason":     result.get("reason", "")
    }
