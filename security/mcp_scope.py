"""
Phase 2 — MCP Scoping
Each conversation is assigned a scope — a list of allowed MCP servers.
Any tool call outside that scope is blocked before it reaches the server.
"""

from dataclasses import dataclass, field
from mcp_servers.client import TOOL_REGISTRY


# ── Scope definitions ─────────────────────────────────────────────────────────
# Maps role/context → allowed MCP servers
SCOPE_PROFILES = {
    "customer_standard": [
        "account",
        "card",
        "transaction",
    ],
    "customer_full": [
        "account",
        "card",
        "transaction",
        "crm",
        "compliance",
    ],
    "agent_support": [
        "account",
        "card",
        "transaction",
        "crm",
        "compliance",
    ],
    "admin": [
        "account",
        "card",
        "transaction",
        "crm",
        "compliance",
    ],
    "readonly": [
        "account",
    ],
}


# ── Conversation scope ────────────────────────────────────────────────────────
@dataclass
class ConversationScope:
    conversation_id:   str
    customer_id:       str
    profile:           str
    allowed_servers:   list = field(default_factory=list)
    blocked_calls:     list = field(default_factory=list)  # audit trail

    def __post_init__(self):
        if not self.allowed_servers:
            self.allowed_servers = SCOPE_PROFILES.get(self.profile, [])

    def is_allowed(self, tool_name: str) -> bool:
        """Check if a tool call is within this conversation's scope."""
        if tool_name not in TOOL_REGISTRY:
            return False
        server_name = TOOL_REGISTRY[tool_name][0]
        return server_name in self.allowed_servers

    def check(self, tool_name: str) -> dict:
        """
        Validate a tool call against scope.

        Returns:
        {
            "allowed":  bool,
            "tool":     str,
            "server":   str,
            "reason":   str,
        }
        """
        if tool_name not in TOOL_REGISTRY:
            result = {
                "allowed": False,
                "tool":    tool_name,
                "server":  "unknown",
                "reason":  f"Tool '{tool_name}' does not exist in registry",
            }
        else:
            server_name = TOOL_REGISTRY[tool_name][0]
            allowed     = server_name in self.allowed_servers

            result = {
                "allowed": allowed,
                "tool":    tool_name,
                "server":  server_name,
                "reason":  (
                    "within scope"
                    if allowed else
                    f"server '{server_name}' not in allowed scope {self.allowed_servers}"
                ),
            }

            if not allowed:
                self.blocked_calls.append({
                    "tool":   tool_name,
                    "server": server_name,
                    "reason": result["reason"],
                })

        return result


# ── Scope registry ────────────────────────────────────────────────────────────
# In Phase 5 this moves to Postgres — for now it's an in-memory dict
_active_scopes: dict[str, ConversationScope] = {}


def create_scope(
    conversation_id: str,
    customer_id:     str,
    profile:         str = "customer_standard"
) -> ConversationScope:
    """Create and register a new conversation scope."""
    scope = ConversationScope(
        conversation_id = conversation_id,
        customer_id     = customer_id,
        profile         = profile,
    )
    _active_scopes[conversation_id] = scope
    return scope


def get_scope(conversation_id: str) -> ConversationScope | None:
    """Retrieve an existing scope by conversation ID."""
    return _active_scopes.get(conversation_id)


def clear_scope(conversation_id: str):
    """Remove scope when conversation ends."""
    _active_scopes.pop(conversation_id, None)
