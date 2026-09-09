from __future__ import annotations
from typing import Any, Dict, List


def _present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _num(value: Any):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _status(label: str, status: str, detail: str = "", source: str = "") -> Dict[str, Any]:
    return {"label": label, "status": status, "detail": detail, "source": source}


def build_presentation(context: Dict[str, Any], readiness: Dict[str, Any], public_information: Dict[str, Any], *, synthetic_poc: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Build deterministic UI support data for Step 5.

    Groq remains responsible only for the short executive narrative. Strengths,
    monitoring flags, missing-data states, compliance states and readiness are
    deterministic so the UI never depends on LLM judgement for credit controls.
    """
    synthetic_poc = synthetic_poc or {}
    borrower = context.get("borrower") or {}
    proposal = context.get("proposal") or {}
    financials = context.get("financials") or {}
    ratios = context.get("ratios") or {}
    credit = context.get("credit") or {}
    collateral = context.get("collateral") or {}
    compliance = context.get("compliance") or {}

    strengths: List[Dict[str, Any]] = []
    attention: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []

    pat = _num(financials.get("pat_cr"))
    nw = _num(financials.get("net_worth_cr"))
    icr = _num(ratios.get("icr"))
    ebitda_margin = _num(ratios.get("ebitda_margin_pct"))
    current_ratio = _num(ratios.get("current_ratio"))
    quick_ratio = _num(ratios.get("quick_ratio"))
    amount = _num(proposal.get("requested_amount_cr"))

    if pat is not None and pat > 0:
        strengths.append({"title": "Profitable operations", "detail": f"PAT ₹{pat:.2f} Cr"})
    if nw is not None and nw > 0:
        strengths.append({"title": "Positive net worth", "detail": f"₹{nw:.2f} Cr"})
    if icr is not None and icr >= 2:
        strengths.append({"title": "Interest coverage", "detail": f"{icr:.2f}x"})
    if ebitda_margin is not None and ebitda_margin > 0:
        strengths.append({"title": "EBITDA margin", "detail": f"{ebitda_margin:.2f}%"})

    if current_ratio is not None and current_ratio < 1.25:
        attention.append({"title": "Liquidity cushion", "detail": f"Current ratio {current_ratio:.2f}x"})
    if quick_ratio is not None and quick_ratio < 1:
        attention.append({"title": "Immediate liquidity", "detail": f"Quick ratio {quick_ratio:.2f}x"})
    if amount is not None and nw not in (None, 0) and amount / nw >= 0.5:
        attention.append({"title": "Material fresh exposure", "detail": f"₹{amount:.2f} Cr proposed vs net worth ₹{nw:.2f} Cr"})

    for label, value in [
        ("Total Debt", financials.get("total_debt_cr")),
        ("Debt / Equity", ratios.get("debt_equity")),
        ("Projected DSCR", ratios.get("dscr")),
        ("Existing Bank Exposure", credit.get("existing_exposure_cr")),
        ("Credit / Bureau Data", credit.get("bureau_score")),
        ("Collateral Coverage", collateral.get("coverage_ratio")),
    ]:
        if not _present(value):
            pending.append({"title": label, "detail": "Pending / not available"})

    verification = [
        _status("Financial documents processed", "completed" if financials.get("latest_fy") else "pending", f"Latest audited period {financials.get('latest_fy') or 'not identified'}", "Annual Reports"),
        _status("MCA / Company details", "completed" if borrower.get("cin") and borrower.get("mca_status") else "pending", f"CIN {borrower.get('cin') or 'pending'} • Status {borrower.get('mca_status') or 'pending'}", "MCA / FileSure"),
        _status("Credit / bureau data", "completed" if _present(credit.get("bureau_score")) else "pending", "Commercial bureau / CMR", credit.get("source") or "Credit verification"),
        _status("Existing bank exposure", "completed" if _present(credit.get("existing_exposure_cr")) else "pending", "BOB and other lender exposure", credit.get("source") or "Bank / bureau"),
        _status("DSCR inputs", "completed" if _present(ratios.get("dscr")) else "pending", "Projected cash flow and debt service", "System calculation"),
        _status("Collateral coverage", "completed" if _present(collateral.get("coverage_ratio")) else "pending", "Valuation and coverage ratio", collateral.get("source") or "Collateral evidence"),
        _status("Public information enrichment", "completed" if public_information.get("mode") not in (None, "off") else "pending", public_information.get("note") or "Public-source checks", public_information.get("mode") or "off"),
    ]

    compliance_rows = []
    mca_status = borrower.get("mca_status")
    compliance_rows.append({"label": "MCA Status", "value": mca_status or "Pending Verification", "status": "verified" if str(mca_status or '').lower() == 'active' else "pending"})
    for label, key in [("KYC", "kyc"), ("Sanctions", "sanctions"), ("PEP", "pep"), ("Adverse Media", "adverse_media")]:
        value = compliance.get(key)
        text = str(value or "").lower()
        if not _present(value):
            status = "pending"
            value = "Pending Verification"
        elif any(x in text for x in ["clear", "verified", "no match", "no material"]):
            status = "verified"
        elif any(x in text for x in ["exception", "match", "adverse", "failed"]):
            status = "exception"
        else:
            status = "review"
        compliance_rows.append({"label": label, "value": value, "status": status})
    po = compliance.get("policy_observations") or []
    compliance_rows.append({"label": "Policy Compliance", "value": "Review observations" if po else "Pending / no exception captured", "status": "review" if po else "pending"})

    completed = sum(1 for x in verification if x["status"] == "completed")
    total = len(verification)
    data_readiness = round(completed / total * 100) if total else 0

    return {
        "strengths": strengths,
        "attention_items": attention,
        "pending_items": pending,
        "verification_status": verification,
        "compliance_status": compliance_rows,
        "data_readiness": {"score": data_readiness, "completed": completed, "total": total},
        "sources": context.get("data_sources") or [],
    }
