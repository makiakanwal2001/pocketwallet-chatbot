#!/bin/bash
# Phase 5 — RBAC curl demo
# Tests all role boundaries against the FastAPI backend.
# Run: bash scripts/test_rbac.sh

BASE="http://localhost:9000"
PASS=0
FAIL=0

check() {
  local desc=$1
  local expected=$2
  local actual=$3
  if echo "$actual" | grep -q "$expected"; then
    echo "  [PASS] $desc"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $desc (expected '$expected' in response)"
    echo "         Got: $actual"
    FAIL=$((FAIL + 1))
  fi
}

echo "========================================"
echo "PocketWallet — Phase 5 RBAC Tests"
echo "========================================"

# ── Login all three roles ─────────────────────────────────────────────────────
echo -e "\n[1] Login as customer (ayesha)"
CUST_TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -d "username=ayesha&password=customer123" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
check "customer login succeeded" "." "$CUST_TOKEN"

echo -e "\n[2] Login as agent (agent01)"
AGENT_TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -d "username=agent01&password=agent123" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
check "agent login succeeded" "." "$AGENT_TOKEN"

echo -e "\n[3] Login as admin (admin01)"
ADMIN_TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -d "username=admin01&password=admin123" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
check "admin login succeeded" "." "$ADMIN_TOKEN"

# ── /auth/me ──────────────────────────────────────────────────────────────────
echo -e "\n[4] GET /auth/me — customer"
R=$(curl -s -H "Authorization: Bearer $CUST_TOKEN" "$BASE/auth/me")
check "role is customer" "customer" "$R"

# ── /chat — all roles can chat ────────────────────────────────────────────────
echo -e "\n[5] POST /chat — customer can chat"
R=$(curl -s -X POST "$BASE/chat" \
  -H "Authorization: Bearer $CUST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the fee for IBFT transfers?"}')
check "chat returns answer" "answer" "$R"
check "chat has intent" "intent" "$R"

# ── /conversations ────────────────────────────────────────────────────────────
echo -e "\n[6] GET /conversations — customer sees own"
R=$(curl -s -H "Authorization: Bearer $CUST_TOKEN" "$BASE/conversations")
check "conversations returned" "." "$R"

# ── /escalations — customer gets 403 ─────────────────────────────────────────
echo -e "\n[7] GET /escalations — customer gets 403"
R=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $CUST_TOKEN" "$BASE/escalations")
check "customer blocked from escalations (403)" "403" "$R"

# ── /escalations — agent can access ──────────────────────────────────────────
echo -e "\n[8] GET /escalations — agent can access"
R=$(curl -s -H "Authorization: Bearer $AGENT_TOKEN" "$BASE/escalations")
check "agent can view escalations" "escalations" "$R"

# ── /audit-log — agent gets 403 ──────────────────────────────────────────────
echo -e "\n[9] GET /audit-log — agent gets 403"
R=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $AGENT_TOKEN" "$BASE/audit-log")
check "agent blocked from audit-log (403)" "403" "$R"

# ── /audit-log — admin can access ────────────────────────────────────────────
echo -e "\n[10] GET /audit-log — admin can access"
R=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE/audit-log")
check "admin can view audit-log" "logs" "$R"

# ── /eval-results — customer gets 403 ────────────────────────────────────────
echo -e "\n[11] GET /eval-results — customer gets 403"
R=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $CUST_TOKEN" "$BASE/eval-results")
check "customer blocked from eval-results (403)" "403" "$R"

# ── /eval-results — admin can access ─────────────────────────────────────────
echo -e "\n[12] GET /eval-results — admin can access"
R=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE/eval-results")
check "admin can view eval-results" "pass_rate" "$R"

# ── Expired/invalid token ─────────────────────────────────────────────────────
echo -e "\n[13] Invalid token gets 401"
R=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer invalid_token_xyz" "$BASE/auth/me")
check "invalid token returns 401" "401" "$R"

echo -e "\n========================================"
echo "RESULTS: $PASS passed, $FAIL failed"
echo "========================================"
