"""
MCP Client
Centralized client the agent uses to call any MCP tool server.
Handles session tokens and maps tool names to server URLs.
"""

import os
import requests

# ── Server registry ───────────────────────────────────────────────────────────
MCP_SERVERS = {
    "account":     os.getenv("ACCOUNT_MCP_URL",     "http://localhost:8001"),
    "card":        os.getenv("CARD_MCP_URL",         "http://localhost:8002"),
    "transaction": os.getenv("TRANSACTION_MCP_URL",  "http://localhost:8003"),
    "crm":         os.getenv("CRM_MCP_URL",          "http://localhost:8004"),
    "compliance":  os.getenv("COMPLIANCE_MCP_URL",   "http://localhost:8005"),
}

# ── Tool → server mapping ─────────────────────────────────────────────────────
TOOL_REGISTRY = {
    "check_balance":            ("account",     "GET",  "/check_balance/{customer_id}"),
    "get_account_info":         ("account",     "GET",  "/get_account_info/{customer_id}"),
    "freeze_card":              ("card",        "POST", "/freeze_card/{customer_id}"),
    "unfreeze_card":            ("card",        "POST", "/unfreeze_card/{customer_id}"),
    "get_card_status":          ("card",        "GET",  "/get_card_status/{customer_id}"),
    "report_lost_stolen":       ("card",        "POST", "/report_lost_stolen/{customer_id}"),
    "get_transaction_history":  ("transaction", "GET",  "/get_transaction_history/{customer_id}"),
    "get_transaction_status":   ("transaction", "GET",  "/get_transaction_status/{customer_id}"),
    "get_customer_history":     ("crm",         "GET",  "/get_customer_history/{customer_id}"),
    "get_open_tickets":         ("crm",         "GET",  "/get_open_tickets/{customer_id}"),
    "get_kyc_status":           ("compliance",  "GET",  "/get_kyc_status/{customer_id}"),
    "kyc_aml_check":            ("compliance",  "GET",  "/kyc_aml_check/{customer_id}"),
}


def call_tool(tool_name: str, customer_id: str, session_token: str) -> dict:
    """
    Call an MCP tool by name.

    Args:
        tool_name:     one of the keys in TOOL_REGISTRY
        customer_id:   e.g. "cust_001"
        session_token: e.g. "session_abc123"

    Returns:
        dict with tool response, or error dict
    """
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {tool_name}"}

    server_name, method, path_template = TOOL_REGISTRY[tool_name]
    base_url = MCP_SERVERS[server_name]

    # Build URL — replace {customer_id} placeholder
    path = path_template.replace("{customer_id}", customer_id)
    url  = f"{base_url}{path}"

    headers = {"Authorization": f"Bearer {session_token}"}

    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=5)
        else:
            resp = requests.post(url, headers=headers, timeout=5)

        resp.raise_for_status()
        return resp.json()

    except requests.exceptions.ConnectionError:
        return {"error": f"{server_name}_mcp server is not reachable at {base_url}"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"error": str(e)}


def health_check_all() -> dict:
    """Check health of all MCP servers."""
    results = {}
    for name, base_url in MCP_SERVERS.items():
        try:
            resp = requests.get(f"{base_url}/health", timeout=3)
            results[name] = "ok" if resp.status_code == 200 else "error"
        except Exception:
            results[name] = "unreachable"
    return results
