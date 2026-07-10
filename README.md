# PocketWallet AI Support Platform

A production-minded AI customer support chatbot for a Pakistani fintech app, built as a portfolio project targeting AI/automation engineering roles. The system handles customer queries in English and Roman Urdu, retrieves answers from internal policy documents, calls live data tools, redacts PII, scores its own confidence, escalates to humans when needed, tracks growth events, and manages prompt versions — all running on local, self-hosted infrastructure with no data leaving the machine.

---

## Architecture

```
Customer Message
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                  SECURITY LAYER                         │
│  PII Redaction → MCP Scope Check → Session Token       │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                  AGENT PIPELINE                         │
│  Language Detection → Sentiment → Intent Classification │
│  Policy Retrieval (ChromaDB RAG) → MCP Tool Call       │
│  Answer Generation (Ollama Llama 3.1 8B)               │
│  Confidence Scoring → Escalation Check                 │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│               MCP TOOL SERVERS (FastAPI)                │
│  Account · Card · Transaction · CRM · Compliance       │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│         OBSERVABILITY, GROWTH & PROMPT MANAGEMENT      │
│  Langfuse Tracing · Drift Detection · A/B Testing      │
│  Redis Event Bus · Segmentation · Lifecycle Messaging  │
│  Versioned Prompt Registry · Shadow Mode               │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│              AUDIT & PERSISTENCE                        │
│  Postgres Audit Log · Conversations · Prompt Versions  │
└─────────────────────────────────────────────────────────┘
```

---

## Key Features

### Intelligent Support Agent
- **Intent Detection** — classifies 7 intents (card freeze, balance, transfer, dispute, KYC, fees, general)
- **Sentiment Analysis** — detects positive / neutral / frustrated / angry and adjusts tone
- **Language Detection** — supports English, Urdu script, and Roman Urdu natively
- **Policy RAG** — retrieves grounded answers from 4 internal policy documents (60 chunks in ChromaDB)
- **Source Citations** — every answer cites its policy source and section number

### Security & Compliance
- **PII Redaction** — Microsoft Presidio with custom Pakistani recognisers (CNIC, card numbers, phone numbers, emails)
- **MCP Scoping** — least-privilege access; each conversation only calls its allowed tool servers
- **Session Tokens** — HMAC-signed tokens tied to conversation ID and customer ID
- **Audit Logging** — append-only Postgres table records every tool call, PII event, and session lifecycle event

### Confidence & Escalation
- **Confidence Scoring** — combines retrieval similarity + LLM self-critique into a 0–1 score
- **Fallback Routing** — routes to Groq (Llama 70B) when local confidence < 0.6
- **Forced Escalation** — legal threats, fraud, account closure, SBP complaints always escalate
- **Escalation Packages** — full context bundles passed to human agents

### Evaluation & Quality
- **35-scenario eval harness** — covers all intents, languages, PII cases, escalation paths, 5 prompt injection attacks
- **LLM-as-judge** — local Ollama grades accuracy, grounding, tone, and safety (0–10)
- **91.4% pass rate** — exceeds the 85% CI threshold
- **GitHub Actions CI** — blocks merges if pass rate drops below 85%

### Observability
- **Langfuse Tracing** — every agent run traced with confidence scores in the dashboard
- **Drift Detection** — alerts when eval pass rate drops 5%+ from baseline
- **A/B Prompt Testing** — compare formal vs empathetic tone across test messages

### Growth Automation
- **Event Tracking** — product events fire into Redis (signup, kyc_incomplete, transfer_failed, inactive_14d)
- **User Segmentation** — 6 behavioral segments (new_signup, kyc_pending, activation_incomplete, inactive_14d, high_value, at_risk)
- **Lifecycle Messaging** — personalised LLM-generated messages per segment and channel (in_app, push_notification)

### Prompt Management
- **Versioned Registry** — all system prompts stored in Postgres with full version history
- **Activate & Rollback** — switch prompt versions without touching code
- **Shadow Mode** — route a percentage of traffic to a new prompt before full rollout

### Auth & RBAC
- **Three roles** — customer (own data only), agent (escalations), admin (everything)
- **JWT authentication** — signed tokens with expiry
- **FastAPI backend** — all endpoints documented at `/docs`

---

## Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| Local LLM | Ollama + Llama 3.1 8B | Free (GPU infra only) |
| Embeddings | Ollama + nomic-embed-text | Free |
| Fallback LLM | Groq API (Llama 70B) | Free tier |
| Vector DB | ChromaDB | Free (self-hosted) |
| MCP Servers | FastAPI + Uvicorn | Free |
| PII Redaction | Microsoft Presidio | Free |
| Database | PostgreSQL 16 | Free (self-hosted) |
| Event Bus | Redis 7 | Free (self-hosted) |
| Observability | Langfuse | Free tier (10K traces/mo) |
| Frontend | Next.js 14 + Tailwind | Free |
| Containers | Docker Compose | Free |

---

## Project Structure

```
pocketwallet-chatbot/
├── agent/
│   ├── graph.py            # Full agent pipeline orchestrator
│   ├── intent.py           # Intent classification
│   ├── sentiment.py        # Sentiment analysis
│   ├── language.py         # Language detection (EN/UR/Roman UR)
│   ├── retrieval.py        # ChromaDB RAG retrieval + citations
│   ├── confidence.py       # Confidence scoring
│   └── escalation.py       # Forced escalation + Groq fallback
├── mcp_servers/
│   ├── client.py           # Centralised MCP tool caller
│   ├── account_mcp/        # check_balance, get_account_info
│   ├── card_mcp/           # freeze_card, report_lost_stolen
│   ├── transaction_mcp/    # get_transaction_history
│   ├── crm_mcp/            # get_customer_history
│   └── compliance_mcp/     # kyc_aml_check, get_kyc_status
├── security/
│   ├── pii_redaction.py    # Presidio PII redaction
│   ├── mcp_scope.py        # Conversation-level MCP scoping
│   ├── session_tokens.py   # HMAC session token lifecycle
│   └── audit_log.py        # Append-only Postgres audit log
├── eval/
│   ├── judge.py            # LLM-as-judge
│   └── scenarios/
│       └── test_conversations.json  # 35 test scenarios
├── observability/
│   ├── tracer.py           # Langfuse tracing
│   ├── drift_detector.py   # Drift detection + alerts
│   └── ab_testing.py       # A/B prompt comparison
├── growth/
│   ├── events.py           # Redis event publishing
│   ├── segmentation.py     # Customer segmentation
│   └── lifecycle_messaging.py  # Automated messaging
├── prompts/
│   └── registry.py         # Versioned prompt registry
├── backend/
│   ├── main.py             # FastAPI app
│   ├── auth.py             # JWT + bcrypt
│   ├── config.py           # Settings
│   └── database.py         # Postgres helpers
├── frontend/
│   ├── app/page.tsx        # Login page
│   ├── components/
│   │   ├── ChatPage.tsx        # Customer chat UI
│   │   ├── AgentDashboard.tsx  # Agent escalation queue
│   │   └── AdminDashboard.tsx  # Admin eval + audit
│   └── lib/api.ts          # API client
├── policies/
│   ├── fee_policy.md
│   ├── kyc_policy.md
│   ├── dispute_policy.md
│   └── card_policy.md
├── scripts/
│   ├── ping_ollama.py
│   ├── residency_check.py
│   ├── embed_policies.py
│   ├── start_mcp_servers.py
│   ├── run_scenarios.py
│   ├── run_eval.py
│   ├── test_*.py
│   └── test_phase*.py
├── .github/workflows/
│   └── ci.yml              # CI gate (85% threshold)
├── docker-compose.yml
└── .env.example
```

---

## Getting Started

### Prerequisites
- Docker Desktop
- Python 3.11+
- Node.js 18+
- 8GB RAM minimum

### Setup

**1. Clone and configure:**
```bash
git clone https://github.com/<you>/pocketwallet-chatbot.git
cd pocketwallet-chatbot
cp .env.example .env
# Add your LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to .env
```

**2. Start infrastructure:**
```bash
docker-compose up -d
```

**3. Pull local models:**
```bash
docker exec -it pocketwallet-chatbot-ollama-1 ollama pull llama3.1:8b
docker exec -it pocketwallet-chatbot-ollama-1 ollama pull nomic-embed-text
```

**4. Install dependencies:**
```bash
pip install -r requirements.txt
pip install presidio-analyzer presidio-anonymizer spacy langfuse redis bcrypt==4.0.1
python -m spacy download en_core_web_sm
```

**5. Embed policy documents:**
```bash
python scripts/embed_policies.py
```

**6. Start MCP servers** (separate terminal):
```bash
python scripts/start_mcp_servers.py
```

**7. Start backend** (separate terminal):
```bash
python -m uvicorn backend.main:app --port 9000 --reload
```

**8. Start frontend** (separate terminal):
```bash
cd frontend && npm install && npm run dev
```

**9. Open the app:**
```
http://localhost:3000
```

Demo credentials:
- Customer: `ayesha` / `customer123`
- Agent: `agent01` / `agent123`
- Admin: `admin01` / `admin123`

---

## Test Results

| Suite | Result |
|-------|--------|
| Phase 1 — CLI scenarios | 7/7 passed |
| Phase 2 — PII redaction | 6/6 passed |
| Phase 2 — MCP scoping | 7/7 passed |
| Phase 2 — Session tokens | 12/12 passed |
| Phase 2 — Audit logging | 9/9 passed |
| Phase 3 — Escalation scenarios | 6/6 passed |
| Phase 4 — Eval harness | 32/35 (91.4%) |
| Phase 5 — RBAC | 15/15 passed |
| Phase 7 — Observability | 3/3 passed |
| Phase 8 — Growth automation | 3/3 passed |
| Phase 9 — Prompt management | 18/18 passed |

---

## Build Phases

| Phase | What was built |
|-------|---------------|
| 0 | Docker stack, local LLM, data residency check |
| 1 | RAG agent, 5 MCP tool servers, 7 CLI scenarios |
| 2 | PII redaction, MCP scoping, session tokens, audit log |
| 3 | Confidence scoring, Groq fallback, forced escalation |
| 4 | 35-scenario eval harness, LLM judge, CI gate |
| 5 | FastAPI backend, JWT auth, three-role RBAC |
| 6 | Next.js chat UI, agent dashboard, admin dashboard |
| 7 | Langfuse tracing, drift detection, A/B prompt testing |
| 8 | Redis event tracking, customer segmentation, lifecycle messaging |
| 9 | Versioned prompt registry, shadow mode, rollback |

---

## Data Residency

All LLM inference runs locally via Ollama. Customer data never leaves the host machine. The `scripts/residency_check.py` script enforces this at runtime — if any external LLM API keys are detected, it fails loudly and exits.
