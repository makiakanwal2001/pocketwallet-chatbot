"""
CRM MCP Server — Port 8004
Tools: get_customer_history, get_open_tickets
"""

from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="CRM MCP Server", version="1.0.0")

CRM_DATA = {
    "cust_001": {
        "open_tickets":   0,
        "total_tickets":  2,
        "last_contact":   "2026-06-15",
        "contact_count_30d": 1,
        "sentiment_history": ["neutral", "positive"],
        "notes": "Loyal customer, no major issues."
    },
    "cust_002": {
        "open_tickets":   1,
        "total_tickets":  3,
        "last_contact":   "2026-07-01",
        "contact_count_30d": 3,
        "sentiment_history": ["neutral", "frustrated", "angry"],
        "notes": "New customer, KYC pending, 2 failed transfers. High frustration."
    },
    "cust_003": {
        "open_tickets":   2,
        "total_tickets":  8,
        "last_contact":   "2026-06-27",
        "contact_count_30d": 4,
        "sentiment_history": ["neutral", "frustrated", "frustrated", "angry"],
        "notes": "Account frozen pending AML review. Disputed transaction open."
    },
}

def verify_token(token: str | None):
    if not token or not token.startswith("Bearer session_"):
        raise HTTPException(status_code=401, detail="Invalid or missing session token")

@app.get("/health")
def health():
    return {"status": "ok", "service": "crm_mcp"}

@app.get("/get_customer_history/{customer_id}")
def get_customer_history(customer_id: str, authorization: str | None = Header(None)):
    verify_token(authorization)
    data = CRM_DATA.get(customer_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"No CRM record for {customer_id}")
    return {"customer_id": customer_id, **data}

@app.get("/get_open_tickets/{customer_id}")
def get_open_tickets(customer_id: str, authorization: str | None = Header(None)):
    verify_token(authorization)
    data = CRM_DATA.get(customer_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"No CRM record for {customer_id}")
    return {
        "customer_id":  customer_id,
        "open_tickets": data["open_tickets"],
        "last_contact": data["last_contact"],
    }
