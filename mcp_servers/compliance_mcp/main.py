"""
Compliance MCP Server — Port 8005
Tools: kyc_aml_check, get_kyc_status
"""

from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="Compliance MCP Server", version="1.0.0")

COMPLIANCE_DATA = {
    "cust_001": {
        "kyc_tier":       1,
        "kyc_status":     "approved",
        "aml_flag":       False,
        "cnic_verified":  True,
        "selfie_verified":True,
        "pending_docs":   [],
        "restrictions":   [],
    },
    "cust_002": {
        "kyc_tier":       0,
        "kyc_status":     "pending",
        "aml_flag":       False,
        "cnic_verified":  False,
        "selfie_verified":False,
        "pending_docs":   ["CNIC front", "CNIC back", "selfie"],
        "restrictions":   ["no_ibft", "balance_limit_10000"],
    },
    "cust_003": {
        "kyc_tier":       2,
        "kyc_status":     "approved",
        "aml_flag":       True,
        "cnic_verified":  True,
        "selfie_verified":True,
        "pending_docs":   ["source_of_funds"],
        "restrictions":   ["account_frozen", "no_transfers"],
    },
}

def verify_token(token: str | None):
    if not token or not token.startswith("Bearer session_"):
        raise HTTPException(status_code=401, detail="Invalid or missing session token")

@app.get("/health")
def health():
    return {"status": "ok", "service": "compliance_mcp"}

@app.get("/get_kyc_status/{customer_id}")
def get_kyc_status(customer_id: str, authorization: str | None = Header(None)):
    verify_token(authorization)
    data = COMPLIANCE_DATA.get(customer_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"No compliance record for {customer_id}")
    return {"customer_id": customer_id, **data}

@app.get("/kyc_aml_check/{customer_id}")
def kyc_aml_check(customer_id: str, authorization: str | None = Header(None)):
    verify_token(authorization)
    data = COMPLIANCE_DATA.get(customer_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"No compliance record for {customer_id}")
    risk_level = "high" if data["aml_flag"] else (
                 "medium" if data["kyc_tier"] == 0 else "low")
    return {
        "customer_id": customer_id,
        "kyc_status":  data["kyc_status"],
        "kyc_tier":    data["kyc_tier"],
        "aml_flag":    data["aml_flag"],
        "risk_level":  risk_level,
        "restrictions":data["restrictions"],
        "pending_docs":data["pending_docs"],
    }
