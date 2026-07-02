"""
Phase 1 — Language Detection
Detects whether customer input is English, Urdu, or Roman Urdu.
Uses Ollama LLM with a structured prompt returning JSON.
"""

import os
import json
import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL   = os.getenv("LLM_MODEL", "llama3.1:8b")

SUPPORTED_LANGUAGES = ["english", "urdu", "roman_urdu"]

PROMPT = """You are a language detection system for a Pakistani fintech app.
Detect the language of the customer message below.

Rules:
- "english": message is written in English
- "urdu": message is written in Urdu script (Arabic letters)
- "roman_urdu": message is Urdu words written in English/Latin letters (common in Pakistan)

Respond ONLY with valid JSON in this exact format:
{{"language": "<english|urdu|roman_urdu>", "confidence": <0.0-1.0>}}

Customer message: {message}"""


def detect_language(message: str) -> dict:
    """
    Returns: {
        "language": "english" | "urdu" | "roman_urdu",
        "confidence": float
    }
    """
    resp = requests.post(f"{OLLAMA_HOST}/api/generate", json={
        "model":  LLM_MODEL,
        "prompt": PROMPT.format(message=message),
        "stream": False,
        "format": "json"
    })
    resp.raise_for_status()

    raw = resp.json()["response"]
    result = json.loads(raw)

    # Validate and normalise
    lang = result.get("language", "english").lower()
    if lang not in SUPPORTED_LANGUAGES:
        lang = "english"

    return {
        "language":   lang,
        "confidence": float(result.get("confidence", 0.8))
    }
