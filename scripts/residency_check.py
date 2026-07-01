import os, sys

FORBIDDEN_KEYS = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
found = [k for k in FORBIDDEN_KEYS if os.getenv(k)]
if found:
    print(f"FAIL: external LLM keys present: {found}")
    sys.exit(1)
print("PASS: no external LLM keys configured")