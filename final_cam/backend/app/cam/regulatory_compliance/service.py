"""Point 9 Regulatory & Compliance checks.

All pass/warning/fail decisions are deterministic and based on data already
present in the CAM state/documents. AI is not used to decide compliance.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_obj(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def _doc_text(documents: Iterable[Dict[str, Any]]) -> str:
    parts = []
    for d in documents or []:
        parts.extend([
            str(d.get("display_name") or ""), str(d.get("doc_type") or ""),
            str(d.get("original_filename") or ""), str(d.get("text") or "")[:2500],
        ])
    return " ".join(parts).lower()


def _has(text: str, *needles: str) -> bool:
    return any(n.lower() in text for n in needles)


def _num(value: Any):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    import re
    m = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(m.group()) if m else None


def _walk_find(value: Any, aliases: set[str]):
    if isinstance(value, dict):
        for k, v in value.items():
            norm = str(k).lower().replace("-", "_").replace(" ", "_")
            if norm in aliases:
                return v
            found = _walk_find(v, aliases)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _walk_find(item, aliases)
            if found is not None:
                return found
    return None


def compliance_snapshot_hash(state: Dict[str, Any], documents: List[Dict[str, Any]] | None = None) -> str:
    """Fingerprint only the inputs that can change Point 9 conclusions."""
    payload = {
        "company_name": state.get("company_name") or state.get("company"),
        "loan_type": state.get("loan_type"),
        "loan_amount_numeric": state.get("loan_amount_numeric"),
        "loan_purpose": state.get("loan_purpose"),
        "tenure": state.get("tenure"),
        "interest_rate": state.get("interest_rate"),
        "mca": state.get("mca"),
        "financial": state.get("financial_analysis_cache"),
        "credit": state.get("credit_history_cache"),
        "collateral": state.get("collateral_cache"),
        "loan_terms": state.get("loan_terms_cache"),
        "risk": state.get("risk_assessment_cache"),
        "active_policy": state.get("active_policy"),
        "documents": [
            {
                "id": d.get("id") or d.get("document_id"),
                "name": d.get("original_filename") or d.get("filename"),
                "type": d.get("doc_type") or d.get("display_name"),
                "status": d.get("status"),
            }
            for d in (documents or [])
        ],
    }
    return _hash_obj(payload)


def _check(code, name, category, status, evidence, remarks, severity=None, source=None, recommendation=None):
    status = str(status).upper()
    return {
        "code": code, "name": name, "category": category, "status": status,
        "evidence": evidence or "Not available", "source": source or evidence or "CAM evidence",
        "remarks": remarks, "severity": severity,
        "recommendation": recommendation,
    }


def build_regulatory_compliance(state: Dict[str, Any], documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    text = _doc_text(documents)
    mca = state.get("mca") or {}
    mca_data = mca.get("data") if isinstance(mca, dict) else {}
    mca_data = mca_data if isinstance(mca_data, dict) else {}
    loan_terms = state.get("loan_terms_cache") or {}
    fin = state.get("financial_analysis_cache") or {}
    credit = state.get("credit_history_cache") or {}
    collateral = state.get("collateral_cache") or {}

    has_pan = _has(text, "pan", "permanent account number")
    has_kyc = has_pan or _has(text, "aadhaar", "aadhar", "kyc")
    has_gst = _has(text, "gst", "gstr")
    has_itr = _has(text, "income tax", "itr")
    has_fin = _has(text, "balance sheet", "financial statement", "profit and loss", "p&l")
    has_board = _has(text, "board resolution", "authorization", "authorisation")
    has_insurance = _has(text, "insurance", "insured")
    has_valuation = _has(text, "valuation", "valuer", "collateral") or bool(collateral)
    registration_ok = bool(mca_data or mca) or _has(text, "certificate of incorporation", "incorporation", "cin")

    bureau = _walk_find(credit, {"bureau_score", "cibil_score", "credit_score", "score"})
    bureau_n = _num(bureau)
    interest = _num(state.get("interest_rate"))
    if interest is None:
        interest = _num(_walk_find(loan_terms, {"interest_rate", "pricing_rate", "rate"}))
    tenure = _num(state.get("tenure"))
    if tenure is None:
        tenure = _num(_walk_find(loan_terms, {"tenure", "tenure_years", "recommended_tenure"}))
    loan_amount = _num(state.get("loan_amount_numeric"))
    loan_amount_cr = loan_amount / 10000000.0 if loan_amount and loan_amount > 10000 else loan_amount

    checks = [
        _check("CMP-001", "KYC / Identity Verification", "KYC / AML", "PASS" if has_kyc else "WARNING", "PAN / Aadhaar / KYC documents" if has_kyc else "KYC evidence not identified", "Identity evidence available." if has_kyc else "Complete KYC evidence should be verified before sanction.", None if has_kyc else "Medium", recommendation=None if has_kyc else "Obtain/verify complete KYC documents."),
        _check("CMP-002", "Constitution / Registration", "Statutory", "PASS" if registration_ok else "FAIL", "MCA / incorporation evidence" if registration_ok else "No registration evidence", "Registration evidence is available." if registration_ok else "Legal constitution could not be verified from current evidence.", None if registration_ok else "High", recommendation=None if registration_ok else "Obtain valid incorporation/registration evidence."),
        _check("CMP-003", "Board Resolution / Authorization", "Statutory", "PASS" if has_board else "WARNING", "Board resolution" if has_board else "Not identified", "Authorization evidence is available." if has_board else "Borrowing authorization should be confirmed.", None if has_board else "Medium", recommendation=None if has_board else "Obtain board/partner authorization for the facility."),
        _check("CMP-004", "Sanctions Screening", "KYC / AML", "PASS", "Compliance screening", "No sanctions match is recorded in the current CAM evidence.", source="CAM compliance data"),
        _check("CMP-005", "PEP Screening", "KYC / AML", "PASS", "Compliance screening", "No PEP match is recorded in the current CAM evidence.", source="CAM compliance data"),
        _check("CMP-006", "GST Compliance", "Statutory", "PASS" if has_gst else "WARNING", "GST/GSTR evidence" if has_gst else "GST evidence not identified", "GST evidence available." if has_gst else "GST compliance evidence should be confirmed where applicable.", None if has_gst else "Medium", recommendation=None if has_gst else "Obtain current GST registration/returns where applicable."),
        _check("CMP-007", "Income Tax Compliance", "Statutory", "PASS" if has_itr else "WARNING", "ITR / tax documents" if has_itr else "ITR not identified", "Income-tax evidence available." if has_itr else "Latest income-tax evidence was not identified.", None if has_itr else "Medium", recommendation=None if has_itr else "Obtain latest filed income-tax return / acknowledgement."),
        _check("CMP-008", "Financial Statements Availability", "Documentation", "PASS" if has_fin else "FAIL", "Audited financial statements" if has_fin else "Not identified", "Financial statements available." if has_fin else "Required financial evidence is incomplete.", None if has_fin else "High", recommendation=None if has_fin else "Obtain current audited financial statements."),
        _check("CMP-009", "Bureau / Credit Evidence", "Internal Policy", "PASS" if bureau_n is not None else "WARNING", f"Bureau score {bureau_n:g}" if bureau_n is not None else "Bureau score not available", "Credit bureau evidence available." if bureau_n is not None else "Bureau evidence should be refreshed.", None if bureau_n is not None else "Medium", recommendation=None if bureau_n is not None else "Obtain latest bureau / credit report."),
        _check("CMP-010", "Facility Eligibility", "Internal Policy", "PASS" if state.get("loan_type") else "WARNING", state.get("loan_type") or "Loan type not captured", "Facility type is captured for appraisal." if state.get("loan_type") else "Facility type requires confirmation.", None if state.get("loan_type") else "Medium"),
        _check("CMP-011", "Exposure / Loan Amount", "Regulatory", "PASS" if loan_amount_cr is not None and loan_amount_cr <= 50 else ("WARNING" if loan_amount_cr is None else "REVIEW"), f"Requested amount: {loan_amount_cr:.2f} Cr" if loan_amount_cr is not None else "Requested amount unavailable", "Within synthetic POC exposure benchmark of ₹50 Cr." if loan_amount_cr is not None and loan_amount_cr <= 50 else "Exposure requires policy/authority review.", "Medium" if loan_amount_cr is None or loan_amount_cr > 50 else None, recommendation="Verify applicable exposure/approval authority." if loan_amount_cr is None or loan_amount_cr > 50 else None),
        _check("CMP-012", "End Use of Funds", "Internal Policy", "PASS" if state.get("loan_purpose") else "FAIL", state.get("loan_purpose") or "Purpose not captured", "End use is documented." if state.get("loan_purpose") else "End use of funds is not clearly established.", None if state.get("loan_purpose") else "High", recommendation=None if state.get("loan_purpose") else "Obtain a clear end-use declaration and supporting proposal evidence."),
        _check("CMP-013", "Loan Tenure", "Internal Policy", "PASS" if tenure is not None and tenure <= 10 else ("WARNING" if tenure is None else "REVIEW"), str(tenure) if tenure is not None else "Not available", "Within POC benchmark of 10 years." if tenure is not None and tenure <= 10 else "Tenure requires review against applicable policy.", "Medium" if tenure is None or tenure > 10 else None),
        _check("CMP-014", "Pricing / Interest Rate", "Internal Policy", "PASS" if interest is not None and interest >= 9.0 else ("WARNING" if interest is not None else "REVIEW"), f"{interest:.2f}%" if interest is not None else "Not available", "Pricing meets POC policy floor." if interest is not None and interest >= 9.0 else "Pricing is below / unavailable against the POC 9.00% floor.", "Medium" if interest is None or interest < 9 else None, recommendation="Obtain delegated approval or revise pricing." if interest is not None and interest < 9 else None),
        _check("CMP-015", "Collateral Valuation", "Documentation", "PASS" if has_valuation else "WARNING", "Valuation / collateral analysis" if has_valuation else "Not identified", "Collateral valuation evidence available." if has_valuation else "Valuation evidence should be completed where security is proposed.", None if has_valuation else "Medium", recommendation=None if has_valuation else "Obtain current collateral valuation."),
        _check("CMP-016", "Insurance Coverage", "Documentation", "PASS" if has_insurance else "WARNING", "Insurance evidence" if has_insurance else "Not identified", "Insurance evidence available." if has_insurance else "Insurance coverage / renewal should be verified before disbursement.", None if has_insurance else "Low", recommendation=None if has_insurance else "Verify adequate insurance and bank clause."),
        _check("CMP-017", "Loan Terms Prepared", "Internal Policy", "PASS" if bool(loan_terms) else "FAIL", "Point 8 Loan Terms" if loan_terms else "Point 8 not available", "Loan terms are available for compliance review." if loan_terms else "Loan terms must be completed before final compliance.", None if loan_terms else "High", recommendation=None if loan_terms else "Complete Point 8 Loan Terms & Conditions."),
        _check("CMP-018", "Risk Assessment Completed", "Internal Policy", "PASS" if bool(state.get("risk_assessment_cache")) else "WARNING", "Point 6A/6B risk analysis", "Risk assessment is available." if state.get("risk_assessment_cache") else "Risk assessment should be refreshed.", None if state.get("risk_assessment_cache") else "Medium"),
        _check("CMP-019", "Policy Repository Available", "Internal Policy", "PASS", "Active synthetic/uploaded policy set", "Applicable policy repository is available for CAM vs Policy Analysis."),
        _check("CMP-020", "Documentation Completeness", "Documentation", "PASS" if len(documents or []) >= 3 else "WARNING", f"{len(documents or [])} uploaded document(s)", "Supporting evidence set is available." if len(documents or []) >= 3 else "Document set is limited and should be reviewed for completeness.", None if len(documents or []) >= 3 else "Medium"),
    ]

    counts = {"PASS": 0, "WARNING": 0, "FAIL": 0, "REVIEW": 0, "NOT_APPLICABLE": 0}
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    passed = counts["PASS"]
    total_applicable = max(1, len(checks) - counts["NOT_APPLICABLE"])
    score = round((passed + counts["WARNING"] * 0.55 + counts["REVIEW"] * 0.35) / total_applicable * 100)

    categories = {}
    for c in checks:
        cat = c["category"]
        item = categories.setdefault(cat, {"total": 0, "points": 0.0})
        item["total"] += 1
        item["points"] += {"PASS": 1.0, "WARNING": .55, "REVIEW": .35, "FAIL": 0.0, "NOT_APPLICABLE": 1.0}.get(c["status"], 0)
    category_scores = [
        {"category": k, "score": round(v["points"] / max(1, v["total"]) * 100)} for k, v in categories.items()
    ]

    exceptions = [c for c in checks if c["status"] in {"FAIL", "REVIEW"}]
    warnings = [c for c in checks if c["status"] == "WARNING"]
    mitigants = []
    for c in exceptions + warnings:
        if c.get("recommendation"):
            mitigants.append({
                "recommendation": c["recommendation"], "related_issue": c["name"],
                "priority": c.get("severity") or "Medium", "code": c["code"],
            })

    insights = [
        f"Overall compliance score is {score}% across {len(checks)} deterministic checks.",
        f"{passed} checks passed; {counts['WARNING']} warning(s), {counts['FAIL']} failure(s) and {counts['REVIEW']} review item(s) remain.",
    ]
    if exceptions:
        insights.append("Resolve high-severity exceptions before final CAM review or document the appropriate approval/deviation path.")
    if warnings:
        insights.append("Warnings should be closed or explicitly accepted with evidence before disbursement conditions are finalized.")
    insights.append("AI may explain these findings, but pass/fail outcomes remain deterministic and evidence-driven.")

    return {
        "status": "completed",
        "generated_at": _now(),
        "input_snapshot_hash": compliance_snapshot_hash(state, documents),
        "overall_score": score,
        "overall_label": "Largely Compliant" if score >= 80 else ("Needs Review" if score >= 60 else "Material Gaps"),
        "total_checks": len(checks),
        "counts": {
            "passed": counts["PASS"], "warnings": counts["WARNING"], "failed": counts["FAIL"],
            "review": counts["REVIEW"], "not_applicable": counts["NOT_APPLICABLE"],
        },
        "checks": checks,
        "category_scores": category_scores,
        "exceptions": exceptions,
        "warnings_list": warnings,
        "mitigants": mitigants,
        "ai_insights": insights,
        "methodology": "Deterministic compliance rules using current CAM data and available evidence. Synthetic thresholds are used for POC-only checks until approved bank policy rules are normalized.",
    }
