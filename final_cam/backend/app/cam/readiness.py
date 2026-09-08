"""Deterministic CAM readiness assessment used by Step 4."""
from typing import Any, Dict, List

WEIGHTS = {
    "documents": 10,
    "borrower_kyc": 15,
    "loan_proposal": 15,
    "financial": 25,
    "credit_banking": 15,
    "collateral": 10,
    "compliance": 10,
}

def _has_fields(documents, needles):
    text = " ".join(str(d.get("display_name") or d.get("doc_type") or d.get("original_filename") or "").lower() for d in documents)
    return any(n in text for n in needles)

def build_readiness(state: Dict[str, Any], documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    has_docs = bool(documents)
    borrower_ok = bool(state.get("company_name") or state.get("company") or (state.get("mca") or {}).get("data"))
    proposal_values = [state.get("loan_type"), state.get("loan_amount_numeric"), state.get("loan_purpose")]
    proposal_count = sum(v not in (None, "") for v in proposal_values)
    proposal_status = "complete" if proposal_count == 3 else ("partial" if proposal_count else "missing")
    financial_ok = _has_fields(documents, ["financial", "balance", "profit", "itr"])
    credit_ok = _has_fields(documents, ["bureau", "cibil", "bank statement", "bank_statement", "credit"])
    collateral_ok = _has_fields(documents, ["collateral", "valuation", "property"])
    compliance_ok = _has_fields(documents, ["kyc", "pan", "aadhaar", "gst", "udyam", "incorporation"])

    checks = [
        ("documents", "Documents", "Required supporting evidence uploaded", "complete" if has_docs else "missing"),
        ("borrower_kyc", "Borrower / KYC", "Borrower identity and registration evidence", "complete" if borrower_ok and compliance_ok else ("partial" if borrower_ok or compliance_ok else "missing")),
        ("loan_proposal", "Loan Proposal", "Facility, purpose and requested amount", proposal_status),
        ("financial", "Financial Data", "Financial statements extracted / available", "complete" if financial_ok else "missing"),
        ("credit_banking", "Credit & Banking", "Bureau / banking evidence available", "complete" if credit_ok else "partial"),
        ("collateral", "Collateral", "Collateral / valuation evidence reviewed", "complete" if collateral_ok else "review_required"),
        ("compliance", "Compliance", "KYC / registration evidence available", "complete" if compliance_ok else "partial"),
    ]
    factor = {"complete": 1.0, "partial": .6, "review_required": .5, "missing": 0.0}
    checklist=[]; score=0.0
    for key,label,description,status in checks:
        earned=round(WEIGHTS[key]*factor[status],1); score += earned
        checklist.append({"key":key,"label":label,"description":description,"status":status,"weight":WEIGHTS[key],"earned":earned})

    missing=[]
    if not collateral_ok:
        missing.append({"item":"Collateral Valuation Report","description":"Latest valuation / security evidence is not available","priority":"high","mandatory":False,"status":"missing","action":"upload"})
    if not credit_ok:
        missing.append({"item":"Latest Bank / Bureau Evidence","description":"Latest banking conduct or bureau evidence is incomplete","priority":"medium","mandatory":False,"status":"partial","action":"review"})
    if proposal_status != "complete":
        missing.append({"item":"Loan Proposal Details","description":"Complete facility, amount and purpose for a richer CAM","priority":"medium","mandatory":False,"status":proposal_status,"action":"review"})

    key_docs=[]
    for d in documents[:8]:
        key_docs.append({
            "name": d.get("original_filename") or d.get("filename") or "Document",
            "type": d.get("display_name") or d.get("doc_type") or "Document",
            "status": d.get("status") or "processed",
            "confidence": d.get("confidence_score"),
            "uploaded_at": d.get("uploaded_at") or d.get("created_at"),
        })
    return {
        "score": int(round(score)),
        "can_start_cam": has_docs,
        "checklist": checklist,
        "documents": key_docs,
        "missing_items": missing,
        "completed_modules": sum(x["status"] == "complete" for x in checklist),
        "in_progress_modules": sum(x["status"] in ("partial","review_required") for x in checklist),
        "pending_modules": sum(x["status"] == "missing" for x in checklist),
        "total_modules": len(checklist),
    }
