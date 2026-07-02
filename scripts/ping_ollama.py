import requests, sys

try:
    resp = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3.1:8b",
        "prompt": "Say hello in one sentence.",
        "stream": False
    })
    resp.raise_for_status()
    print(resp.json()["response"])
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)