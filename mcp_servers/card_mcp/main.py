"""
Card MCP Server — Port 8002
Tools: freeze_card, unfreeze_card, get_card_status, report_lost_stolen
"""

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Card MCP Server", version="1.0.0")

# ── Mock card data ────────────────────────────────────────────────────────────
CARDS = {
    "cust_001": {
        "card_last4":   "4821",
        "card_type":    "physical",
        "card_status":  "active",
        "international_enabled": False,
        "daily_limit_pkr": 200000,
    },
    "cust_002": {
        "card_last4":   "9034",
        "card_type":    "virtual",
        "card_status":  "active",
        "international_enabled": False,
        "daily_limit_pkr": 25000,
    },
    "cust_003": {
        "card_last4":   "1156",
        "card_type":    "physical",
        "card_status":  "blocked",
        "international_enabled": True,
        "daily_limit_pkr": 500000,
    },
}

def verify_token(token: str | None):
    if not token or not token.startswith("Bearer session_"):
        raise HTTPException(status_code=401, detail="Invalid or missing session token")

@app.get("/health")
def health():
    return {"status": "ok", "service": "card_mcp"}


@app.get("/get_card_status/{customer_id}")
def get_card_status(customer_id: str, authorization: str | None = Header(None)):
    verify_token(authorization)
    card = CARDS.get(customer_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"No card found for {customer_id}")
    return {"customer_id": customer_id, **card}


@app.post("/freeze_card/{customer_id}")
def freeze_card(customer_id: str, authorization: str | None = Header(None)):
    verify_token(authorization)
    card = CARDS.get(customer_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"No card found for {customer_id}")
    if card["card_status"] == "blocked":
        return {"customer_id": customer_id, "result": "already_frozen",
                "card_last4": card["card_last4"],
                "message": "Card is already blocked."}
    CARDS[customer_id]["card_status"] = "blocked"
    return {
        "customer_id": customer_id,
        "result":      "success",
        "card_last4":  card["card_last4"],
        "message":     f"Card ending {card['card_last4']} has been frozen immediately."
    }


@app.post("/unfreeze_card/{customer_id}")
def unfreeze_card(customer_id: str, authorization: str | None = Header(None)):
    verify_token(authorization)
    card = CARDS.get(customer_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"No card found for {customer_id}")
    CARDS[customer_id]["card_status"] = "active"
    return {
        "customer_id": customer_id,
        "result":      "success",
        "card_last4":  card["card_last4"],
        "message":     f"Card ending {card['card_last4']} has been unfrozen."
    }


@app.post("/report_lost_stolen/{customer_id}")
def report_lost_stolen(customer_id: str, authorization: str | None = Header(None)):
    verify_token(authorization)
    card = CARDS.get(customer_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"No card found for {customer_id}")
    CARDS[customer_id]["card_status"] = "blocked"
    return {
        "customer_id":    customer_id,
        "result":         "success",
        "card_last4":     card["card_last4"],
        "replacement_eta": "5-7 business days",
        "message":        f"Card ending {card['card_last4']} blocked. Replacement card will arrive in 5-7 business days."
    }
