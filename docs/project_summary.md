# PocketWallet AI Support Platform — Project Summary

**Type:** Portfolio project  
**Target role:** AI / Automation Engineer (Fintech)  
**Stack:** Python, FastAPI, Next.js, Ollama, ChromaDB, Postgres, Redis, Langfuse  
**Total phases:** 9  
**Total test cases:** 121 (119 passing)  
**Eval pass rate:** 91.4% (threshold: 85%)

---

## What Was Built

A production-minded AI customer support platform for a fictional Pakistani fintech app called PocketWallet. The system handles customer queries in English and Roman Urdu, retrieves grounded answers from internal policy documents using RAG, calls live data tool servers, redacts PII before anything reaches the LLM, scores its own confidence, escalates sensitive topics to human agents, tracks product events for growth automation, and manages prompt versions with shadow mode rollout — all running on local, self-hosted infrastructure with no customer data leaving the machine.

---

## Phase-by-Phase Summary

### Phase 0 — Scaffolding & Environment
Set up the local infrastructure before writing any agent logic. Three Docker services: Postgres 16 (persistence), Redis 7 (event bus), and Ollama with Llama 3.1 8B (local LLM inference). Wrote two validation scripts — one that pings Ollama and gets a real LLM response, and one that checks no external API keys are present. Data residency enforced from day one.
**DoD:** docker-compose up works, CLI returns a real LLM response, residency check passes. ✓

### Phase 1 — Core Agent Loop
Built the brain of the chatbot — CLI-first, no UI. Created 4 policy documents (fees, KYC, disputes, card policy), embedded 60 chunks into ChromaDB. Built language detection (English/Urdu/Roman Urdu), sentiment analysis, and intent classification (7 intents). Created 5 standalone MCP tool servers as FastAPI services. Wired into an agent graph with 7 CLI test scenarios.
**DoD:** 7/7 scenarios pass, policy-grounded answers with citations, 6 MCP tool calls triggered. ✓

### Phase 2 — Security Layer
PII redaction using Microsoft Presidio with custom Pakistani recognisers (CNIC, card, phone, email, name). MCP scoping — each conversation only calls allowed servers. HMAC-signed session tokens with tamper detection. Append-only Postgres audit log.
**DoD:** 34 tests passing. ✓

### Phase 3 — Confidence Scoring & Escalation
Confidence scoring combining retrieval similarity and LLM self-critique. Groq fallback when confidence < 0.6. Forced escalation for legal threats, fraud, account closure, and SBP complaints. Escalation context packages for human agents.
**DoD:** 6/6 escalation scenarios pass. ✓

### Phase 4 — Evaluation Harness
35 scripted test conversations including 5 prompt injection attacks. LLM-as-judge (local Ollama) grades accuracy, grounding, tone, and safety. GitHub Actions CI gate at 85% threshold.
**DoD:** 91.4% pass rate, CI gate passing. ✓

### Phase 5 — Auth & RBAC
FastAPI backend with JWT authentication and three-role RBAC (customer, agent, admin). All endpoints documented at /docs.
**DoD:** 15/15 RBAC tests pass, all role boundaries enforced. ✓

### Phase 6 — Chat UI & Dashboards
Next.js 14 frontend with customer chat interface (suggested actions, intent/sentiment badges), agent dashboard (escalation queue), and admin dashboard (eval results, audit log).
**DoD:** All three dashboards functional and role-gated. ✓

### Phase 7 — Observability & Quality Scoring
Langfuse tracing for every agent run. Drift detection with 5% alert threshold. A/B prompt comparison with latency tracking.
**DoD:** 3/3 observability tests pass, traces visible in Langfuse. ✓

### Phase 8 — Growth Automation
Redis Pub/Sub event tracking (8 event types). Customer segmentation across 6 behavioral segments. Personalised LLM-generated lifecycle messages per segment and channel.
**DoD:** 3/3 growth tests pass. ✓

### Phase 9 — Prompt Management
All system prompts in a versioned Postgres table. Create, activate, rollback prompt versions without touching code. Shadow mode routes configurable traffic percentage to new prompts.
**DoD:** 18/18 prompt management tests pass. ✓

---

## Test Results Summary

| Suite | Tests | Result |
|-------|-------|--------|
| Phase 1 — CLI scenarios | 7 | 7/7 ✓ |
| Phase 2 — PII redaction | 6 | 6/6 ✓ |
| Phase 2 — MCP scoping | 7 | 7/7 ✓ |
| Phase 2 — Session tokens | 12 | 12/12 ✓ |
| Phase 2 — Audit logging | 9 | 9/9 ✓ |
| Phase 3 — Escalation | 6 | 6/6 ✓ |
| Phase 4 — Eval harness | 35 | 32/35 (91.4%) ✓ |
| Phase 5 — RBAC | 15 | 15/15 ✓ |
| Phase 7 — Observability | 3 | 3/3 ✓ |
| Phase 8 — Growth automation | 3 | 3/3 ✓ |
| Phase 9 — Prompt management | 18 | 18/18 ✓ |
| **Total** | **121** | **119/121** |

---

## Key Design Decisions

**Why local LLM?** SBP data residency requirements — customer financial data cannot leave local servers.

**Why MCP tool servers?** Least-privilege principle — scoped access limits blast radius if any server is compromised.

**Why local LLM-as-judge?** Even fake test data should not leave the perimeter — no external eval API calls needed.

**Why append-only audit log?** Financial regulators require full traceability — no record can ever be edited or deleted.

---

## Running the Full Stack

```bash
docker-compose up -d
python scripts/start_mcp_servers.py          # Terminal 2
python -m uvicorn backend.main:app --port 9000 --reload  # Terminal 3
cd frontend && npm run dev                   # Terminal 4
python scripts/embed_policies.py             # Once per Docker restart
```

Open http://localhost:3000 — login as ayesha/customer123, agent01/agent123, or admin01/admin123.
