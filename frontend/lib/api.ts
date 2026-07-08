/**
 * Phase 6 — API Client
 * Connects the Next.js frontend to the Phase 5 FastAPI backend.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:9000";

export interface LoginResponse {
  access_token: string;
  token_type:   string;
  role:         string;
}

export interface ChatResponse {
  conversation_id:   string;
  message:           string;
  answer:            string;
  intent:            string;
  sentiment:         string;
  tool_called:       string;
  citations:         string[];
  escalated:         boolean;
  escalation_reason: string | null;
  pii_detected:      boolean;
}

export interface Conversation {
  conversation_id: string;
  customer_id:     string;
  username:        string;
  messages:        Message[];
  created_at:      string;
  updated_at:      string;
}

export interface Message {
  role:      "user" | "assistant";
  content:   string;
  timestamp: string;
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function login(
  username: string,
  password: string
): Promise<LoginResponse> {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);

  const resp = await fetch(`${BASE_URL}/auth/login`, {
    method:  "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body:    form.toString(),
  });

  if (!resp.ok) throw new Error("Invalid username or password");
  return resp.json();
}

export async function getMe(token: string) {
  const resp = await fetch(`${BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error("Unauthorized");
  return resp.json();
}

// ── Chat ──────────────────────────────────────────────────────────────────────
export async function sendMessage(
  token:   string,
  message: string
): Promise<ChatResponse> {
  const resp = await fetch(`${BASE_URL}/chat`, {
    method:  "POST",
    headers: {
      Authorization:  `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });
  if (!resp.ok) throw new Error("Chat request failed");
  return resp.json();
}

// ── Conversations ─────────────────────────────────────────────────────────────
export async function getConversations(token: string): Promise<Conversation[]> {
  const resp = await fetch(`${BASE_URL}/conversations`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error("Failed to fetch conversations");
  return resp.json();
}

// ── Escalations ───────────────────────────────────────────────────────────────
export async function getEscalations(token: string) {
  const resp = await fetch(`${BASE_URL}/escalations`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error("Access denied");
  return resp.json();
}

// ── Admin ─────────────────────────────────────────────────────────────────────
export async function getEvalResults(token: string) {
  const resp = await fetch(`${BASE_URL}/eval-results`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error("Access denied");
  return resp.json();
}

export async function getAuditLog(token: string) {
  const resp = await fetch(`${BASE_URL}/audit-log`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error("Access denied");
  return resp.json();
}
