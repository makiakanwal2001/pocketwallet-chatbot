"""
Phase 5 — RBAC Tests (Python version)
Tests all role boundaries against the FastAPI backend.
"""

import requests
import sys

BASE  = "http://localhost:9000"
PASS  = 0
FAIL  = 0

def check(desc: str, expected: str, actual: str):
    global PASS, FAIL
    if expected in str(actual):
        print(f"  [PASS] {desc}")
        PASS += 1
    else:
        print(f"  [FAIL] {desc}")
        print(f"         Expected '{expected}' in: {str(actual)[:120]}")
        FAIL += 1

def login(username: str, password: str) -> str:
    resp = requests.post(f"{BASE}/auth/login",
                         data={"username": username, "password": password})
    if resp.status_code == 200:
        return resp.json()["access_token"]
    return ""

def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def main():
    print("=" * 50)
    print("PocketWallet — Phase 5 RBAC Tests")
    print("=" * 50)

    # ── Login ─────────────────────────────────────────
    print("\n[1] Login as customer (ayesha)")
    cust_token = login("ayesha", "customer123")
    check("customer login succeeded", "ey", cust_token)

    print("\n[2] Login as agent (agent01)")
    agent_token = login("agent01", "agent123")
    check("agent login succeeded", "ey", agent_token)

    print("\n[3] Login as admin (admin01)")
    admin_token = login("admin01", "admin123")
    check("admin login succeeded", "ey", admin_token)

    # ── /auth/me ──────────────────────────────────────
    print("\n[4] GET /auth/me — customer")
    r = requests.get(f"{BASE}/auth/me", headers=headers(cust_token))
    check("role is customer", "customer", r.text)

    # ── /chat ─────────────────────────────────────────
    print("\n[5] POST /chat — customer can chat")
    r = requests.post(f"{BASE}/chat",
                      headers=headers(cust_token),
                      json={"message": "What is the fee for IBFT transfers?"})
    check("chat returns answer", "answer", r.text)
    check("chat has intent",     "intent", r.text)

    # ── /conversations ────────────────────────────────
    print("\n[6] GET /conversations — customer")
    r = requests.get(f"{BASE}/conversations", headers=headers(cust_token))
    check("conversations returned", "200", str(r.status_code))

    # ── /escalations — customer gets 403 ──────────────
    print("\n[7] GET /escalations — customer gets 403")
    r = requests.get(f"{BASE}/escalations", headers=headers(cust_token))
    check("customer blocked from escalations (403)", "403", str(r.status_code))

    # ── /escalations — agent can access ───────────────
    print("\n[8] GET /escalations — agent can access")
    r = requests.get(f"{BASE}/escalations", headers=headers(agent_token))
    check("agent can view escalations", "escalations", r.text)

    # ── /audit-log — agent gets 403 ───────────────────
    print("\n[9] GET /audit-log — agent gets 403")
    r = requests.get(f"{BASE}/audit-log", headers=headers(agent_token))
    check("agent blocked from audit-log (403)", "403", str(r.status_code))

    # ── /audit-log — admin can access ─────────────────
    print("\n[10] GET /audit-log — admin can access")
    r = requests.get(f"{BASE}/audit-log", headers=headers(admin_token))
    check("admin can view audit-log", "logs", r.text)

    # ── /eval-results — customer gets 403 ─────────────
    print("\n[11] GET /eval-results — customer gets 403")
    r = requests.get(f"{BASE}/eval-results", headers=headers(cust_token))
    check("customer blocked from eval-results (403)", "403", str(r.status_code))

    # ── /eval-results — admin can access ──────────────
    print("\n[12] GET /eval-results — admin can access")
    r = requests.get(f"{BASE}/eval-results", headers=headers(admin_token))
    check("admin can view eval-results", "pass_rate", r.text)

    # ── Invalid token gets 401 ────────────────────────
    print("\n[13] Invalid token gets 401")
    r = requests.get(f"{BASE}/auth/me",
                     headers={"Authorization": "Bearer invalid_token_xyz"})
    check("invalid token returns 401", "401", str(r.status_code))

    # ── Claim escalation ──────────────────────────────
    print("\n[14] POST /escalations/{id}/claim — agent can claim")
    r = requests.post(f"{BASE}/escalations/ESC_001/claim",
                      headers=headers(agent_token),
                      json={"note": "Taking ownership of this case"})
    check("agent can claim escalation", "claimed", r.text)

    print(f"\n{'=' * 50}")
    print(f"RESULTS: {PASS} passed, {FAIL} failed")
    print(f"Phase 5 DoD: {'MET ✓' if FAIL == 0 else 'NOT MET ✗'}")
    print("=" * 50)

    sys.exit(0 if FAIL == 0 else 1)

if __name__ == "__main__":
    main()
