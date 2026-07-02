"""
Transaction MCP Server — Port 8003
Tools: get_transaction_status, get_transaction_history
"""

from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="Transaction MCP Server", version="1.0.0")

TRANSACTIONS = {
    "cust_001": [
        {"txn_id": "TXN_A1001", "date": "2026-06-28", "amount_pkr": 5000,
         "type": "IBFT", "merchant": "HBL Bank", "status": "completed"},
        {"txn_id": "TXN_A1002", "date": "2026-06-30", "amount_pkr": 1200,
         "type": "POS", "merchant": "Carrefour Karachi", "status": "completed"},
        {"txn_id": "TXN_A1003", "date": "2026-07-01", "amount_pkr": 8500,
         "type": "online", "merchant": "Daraz.pk", "status": "pending"},
    ],
    "cust_002": [
        {"txn_id": "TXN_B2001", "date": "2026-06-29", "amount_pkr": 500,
         "type": "POS", "merchant": "Imtiaz Store", "status": "completed"},
        {"txn_id": "TXN_B2002", "date": "2026-07-01", "amount_pkr": 2000,
         "type": "IBFT", "merchant": "Meezan Bank", "status": "failed"},
    ],
    "cust_003": [
        {"txn_id": "TXN_C3001", "date": "2026-06-25", "amount_pkr": 50000,
         "type": "IBFT", "merchant": "Allied Bank", "status": "completed"},
        {"txn_id": "TXN_C3002", "date": "2026-06-27", "amount_pkr": 12000,
         "type": "online", "merchant": "Unknown Merchant", "status": "disputed"},
    ],
}

def verify_token(token: str | None):
    if not token or not token.startswith("Bearer session_"):
        raise HTTPException(status_code=401, detail="Invalid or missing session token")

@app.get("/health")
def health():
    return {"status": "ok", "service": "transaction_mcp"}

@app.get("/get_transaction_history/{customer_id}")
def get_transaction_history(customer_id: str, authorization: str | None = Header(None)):
    verify_token(authorization)
    txns = TRANSACTIONS.get(customer_id, [])
    return {"customer_id": customer_id, "transactions": txns, "count": len(txns)}

@app.get("/get_transaction_status/{txn_id}")
def get_transaction_status(txn_id: str, authorization: str | None = Header(None)):
    verify_token(authorization)
    for txns in TRANSACTIONS.values():
        for txn in txns:
            if txn["txn_id"] == txn_id:
                return txn
    raise HTTPException(status_code=404, detail=f"Transaction {txn_id} not found")
