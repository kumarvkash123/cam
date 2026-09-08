"""Loan Terms & Conditions (CAM Point 8).

Builds a deterministic, auditable proposed facility structure from proposal data
and upstream CAM outputs (financial, credit, risk and collateral). Policy values
in this POC are configurable defaults and are clearly labelled as such. The LLM
is used only to phrase the final commentary from already-structured facts.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.cam.llm_gateway import chat as llm_chat, LLMGatewayError

POC_POLICY = {
    "max_amount_cr": 25.0,
    "max_tenor_months": 60,
    "max_moratorium_months": 6,
    "min_security_coverage": 1.50,
    "min_dscr": 1.20,
    "min_stress_dscr": 1.00,
}

MISSING = (None, "", "—", "N/A", "Not available")


def _num(v: Any) -> Optional[float]:
    if v in MISSING:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def _cr(v: Any) -> Optional[float]:
    n = _num(v)
    if n is None:
        return None
    s = str(v).lower()
    if "crore" in s or re.search(r"\bcr\b", s):
        return round(n, 4)
    if "lakh" in s or "lac" in s:
        return round(n / 100.0, 4)
    if abs(n) >= 100000:
        return round(n / 10000000.0, 4)
    return round(n, 4)


def _months(v: Any) -> Optional[int]:
    n = _num(v)
    if n is None:
        return None
    s = str(v).lower()
    if "year" in s:
        return int(round(n * 12))
    return int(round(n))


def _pct(v: Any) -> Optional[float]:
    n = _num(v)
    return round(n, 4) if n is not None else None


def _fmt(v: Any, suffix="") -> str:
    return "Not available" if v is None else f"{v}{suffix}"


def _ratio(financial: Dict[str, Any], key: str) -> Optional[float]:
    for r in financial.get("ratios") or []:
        if r.get("key") == key:
            return _num(r.get("value"))
    return None


def _stress_dscr(financial: Dict[str, Any]) -> Optional[float]:
    rows = financial.get("stress_testing") or financial.get("stress_test") or financial.get("stress_scenarios") or []
    for r in rows:
        name = str(r.get("scenario") or "").lower()
        if "severe" in name:
            return _num(r.get("dscr"))
    return None


def _status(actual, comparator, threshold):
    if actual is None:
        return "Not Assessed"
    ok = actual <= threshold if comparator == "max" else actual >= threshold
    return "Compliant" if ok else "Deviation"


def _requested_vs_policy(state, financial, collateral, overrides):
    requested_amount = _cr(state.get("loan_amount_numeric") or state.get("loan_amount"))
    requested_tenor = _months(state.get("tenure"))
    requested_moratorium = _months(state.get("moratorium") or state.get("moratorium_months"))
    amount = _cr(overrides.get("proposed_amount_cr")) if overrides.get("proposed_amount_cr") not in MISSING else (min(requested_amount, POC_POLICY["max_amount_cr"]) if requested_amount is not None else None)
    proposed_tenor = _months(overrides.get("tenor_months")) if overrides.get("tenor_months") not in MISSING else (min(requested_tenor, POC_POLICY["max_tenor_months"]) if requested_tenor is not None else None)
    proposed_moratorium = _months(overrides.get("moratorium_months")) if overrides.get("moratorium_months") not in MISSING else (min(requested_moratorium, POC_POLICY["max_moratorium_months"]) if requested_moratorium is not None else None)
    rate = _pct(overrides.get("interest_rate")) if overrides.get("interest_rate") not in MISSING else _pct(state.get("interest_rate"))
    coverage = _num((collateral.get("coverage") or {}).get("coverage_ratio"))
    dscr = _ratio(financial, "dscr")
    stress_dscr = _stress_dscr(financial)

    rows = [
        {"parameter":"Facility Amount","requested":requested_amount,"proposed":amount,"unit":"cr","policy":f"≤ ₹ {POC_POLICY['max_amount_cr']:.2f} Cr","status":_status(amount,"max",POC_POLICY["max_amount_cr"])},
        {"parameter":"Tenor","requested":requested_tenor,"proposed":proposed_tenor,"unit":"months","policy":f"≤ {POC_POLICY['max_tenor_months']} Months","status":_status(proposed_tenor,"max",POC_POLICY["max_tenor_months"])},
        {"parameter":"Moratorium","requested":requested_moratorium,"proposed":proposed_moratorium,"unit":"months","policy":f"≤ {POC_POLICY['max_moratorium_months']} Months","status":_status(proposed_moratorium,"max",POC_POLICY["max_moratorium_months"])},
        {"parameter":"Interest Rate","requested":_pct(state.get("interest_rate")),"proposed":rate,"unit":"pct","policy":"As per pricing policy","status":"Compliant" if rate is not None else "Not Assessed"},
        {"parameter":"Security Coverage","requested":coverage,"proposed":coverage,"unit":"x","policy":f"≥ {POC_POLICY['min_security_coverage']:.2f}x","status":_status(coverage,"min",POC_POLICY["min_security_coverage"])},
        {"parameter":"DSCR (Base Case)","requested":dscr,"proposed":dscr,"unit":"x","policy":f"≥ {POC_POLICY['min_dscr']:.2f}x","status":_status(dscr,"min",POC_POLICY["min_dscr"])},
        {"parameter":"DSCR (Severe Stress)","requested":stress_dscr,"proposed":stress_dscr,"unit":"x","policy":f"≥ {POC_POLICY['min_stress_dscr']:.2f}x","status":_status(stress_dscr,"min",POC_POLICY["min_stress_dscr"])},
        {"parameter":"Repayment Frequency","requested":state.get("repayment"),"proposed":overrides.get("repayment") or state.get("repayment"),"unit":"text","policy":"As per product policy","status":"Compliant" if (overrides.get("repayment") or state.get("repayment")) else "Not Assessed"},
    ]
    for r in rows:
        if r["parameter"] in ("Facility Amount", "Tenor", "Moratorium") and r["requested"] is not None and r["proposed"] is not None and r["requested"] != r["proposed"]:
            r["status"] = "Modified"
    return rows


def _pricing(state, overrides):
    rate = _pct(overrides.get("interest_rate")) if overrides.get("interest_rate") not in MISSING else _pct(state.get("interest_rate"))
    benchmark = _pct(state.get("benchmark_rate") or state.get("base_rate"))
    spread = round((rate - benchmark) * 100, 2) if rate is not None and benchmark is not None else None
    return {
        "benchmark_name": state.get("benchmark_name") or "Bank benchmark / pricing grid",
        "benchmark_rate": benchmark,
        "spread_bps": spread,
        "indicative_rate": rate,
        "rate_type": state.get("rate_type") or "Not available",
        "reset_frequency": state.get("reset_frequency") or "Not available",
        "processing_fee": state.get("processing_fee") or "As per applicable policy",
        "other_charges": state.get("other_charges") or "As applicable",
        "notice": "Pricing values are displayed only when present in proposal/pricing data; the LLM does not determine rates."
    }


def _security(collateral):
    securities = collateral.get("securities") or []
    primary = [s for s in securities if str(s.get("category") or "").lower() == "primary"]
    others = [s for s in securities if s not in primary]
    def desc(items):
        return "; ".join(str(x.get("security") or x.get("description") or "Security") for x in items[:3]) or "Not available"
    cov = collateral.get("coverage") or {}
    checks = collateral.get("validation_checks") or []
    charge = next((x for x in checks if "charge" in str(x.get("check") or "").lower()), None)
    insurance = next((x for x in checks if "insurance" in str(x.get("check") or "").lower()), None)
    return {
        "primary_security": desc(primary),
        "collateral_security": desc(others),
        "coverage_ratio": _num(cov.get("coverage_ratio")),
        "eligible_value_cr": _cr(cov.get("eligible_value_cr") or (collateral.get("summary") or {}).get("eligible_value_cr")),
        "charge_creation": (charge or {}).get("detail") or "Not available",
        "insurance": (insurance or {}).get("detail") or "Not available",
        "valuation_validity": "See collateral valuation analysis",
    }


def _conditions(state, risk, collateral):
    concerns = risk.get("key_concerns") or risk.get("concerns") or []
    observations = collateral.get("observations") or []
    text = " ".join([str(x.get("text") if isinstance(x, dict) else x) for x in concerns + observations]).lower()

    pre = [
        "Execute facility and security documents in form acceptable to the bank.",
        "Complete applicable charge / mortgage creation and registration formalities.",
        "Ensure legal title / security documentation is satisfactory before disbursement.",
        "Maintain valid insurance with appropriate bank clause where applicable.",
    ]
    post = [
        "Submit financial information and covenant-compliance data at agreed periodicity.",
        "Maintain valid insurance and renew before expiry.",
        "Permit periodic monitoring / inspection of charged assets where applicable.",
    ]
    if "receivable" in text or "working capital" in text or "utilization" in text:
        post += ["Submit periodic debtor ageing / stock statements and working-capital information."]
    if "charge" in text or "existing charge" in text:
        pre += ["Resolve / document existing lender charge position and obtain required NOC / pari-passu consent before disbursement."]
    if "valuation" in text or "revaluation" in text:
        pre += ["Obtain fresh / acceptable valuation where the existing valuation is outside the bank's permitted validity period."]
    if "insurance" in text and "expir" in text:
        pre += ["Renew expiring insurance before disbursement or within the approved condition timeline."]
    if "stress" in text or "dscr" in text:
        post += ["Monitor debt-servicing capacity and DSCR at each financial review."]
    return list(dict.fromkeys(pre)), list(dict.fromkeys(post))


def _covenants(financial, collateral, risk):
    rows = []
    if _ratio(financial, "dscr") is not None:
        rows.append({"group":"Financial Covenants","text":f"Maintain DSCR ≥ {POC_POLICY['min_dscr']:.2f}x","source":"POC policy threshold"})
    if _ratio(financial, "current_ratio") is not None:
        rows.append({"group":"Financial Covenants","text":"Maintain Current Ratio ≥ 1.25x","source":"POC policy threshold"})
    if _ratio(financial, "debt_equity") is not None:
        rows.append({"group":"Financial Covenants","text":"Maintain Debt / Equity ≤ 3.00x","source":"POC policy threshold"})
    cov = _num((collateral.get("coverage") or {}).get("coverage_ratio"))
    if cov is not None:
        rows.append({"group":"Collateral Covenants","text":f"Maintain security coverage ≥ {POC_POLICY['min_security_coverage']:.2f}x","source":"POC policy threshold"})
        rows.append({"group":"Collateral Covenants","text":"Maintain valid insurance over charged assets","source":"Collateral control"})
    concern_text = " ".join(str(x.get("text") if isinstance(x, dict) else x) for x in (risk.get("key_concerns") or risk.get("concerns") or [])).lower()
    if "working capital" in concern_text or "receivable" in concern_text or "utilization" in concern_text:
        rows.append({"group":"Operational Covenants","text":"Submit periodic stock / debtor ageing information","source":"Risk mitigation"})
    rows.append({"group":"Operational Covenants","text":"Route material operating collections through designated banking arrangements, where stipulated in sanction","source":"Subject to sanction terms"})
    return rows


def _deviations(comparison, risk):
    out = []
    for r in comparison:
        if r["status"] in ("Deviation", "Modified"):
            action = "Officer / delegated authority review required" if r["status"] == "Deviation" else "Proposed term modified to align with POC threshold"
            out.append({"parameter":r["parameter"],"details":f"Requested: {_display(r['requested'], r['unit'])}; Proposed: {_display(r['proposed'], r['unit'])}; Policy: {r['policy']}","status":r["status"],"action":action})
    return out


def _display(v, unit):
    if v in MISSING:
        return "Not available"
    if unit == "cr": return f"₹ {float(v):.2f} Cr"
    if unit == "months": return f"{int(v)} Months"
    if unit == "pct": return f"{float(v):.2f}%"
    if unit == "x": return f"{float(v):.2f}x"
    return str(v)


def _commentary(payload, include_ai=True):
    fallback = (
        "The proposed loan terms have been structured from the available proposal, financial, risk and collateral outputs. "
        "Any item marked Modified, Deviation or Not Assessed requires credit-officer review and applicable policy validation before sanction."
    )
    if not include_ai:
        return {"source":"deterministic","text":fallback}
    compact = {
        "facility": payload["facility"], "comparison": payload["comparison"], "pricing": payload["pricing"],
        "repayment": payload["repayment"], "security": payload["security"], "covenants": payload["covenants"],
        "pre_disbursement_conditions": payload["pre_disbursement_conditions"],
        "post_disbursement_conditions": payload["post_disbursement_conditions"], "deviations": payload["deviations"]
    }
    system = (
        "You are drafting CAM Point 8 Loan Terms & Conditions for a bank credit officer. "
        "Use only the supplied structured facts. Do not invent pricing, amounts, policy limits, covenants or approvals. "
        "Write one concise professional paragraph (120-180 words). Explicitly state when data is unavailable or a POC threshold is being used."
    )
    try:
        text = llm_chat([{"role":"system","content":system},{"role":"user","content":json.dumps(compact, ensure_ascii=False)}], temperature=0.1)
        return {"source":"ai_generated","text":str(text).strip()}
    except Exception as exc:
        return {"source":"deterministic","text":fallback,"error":str(exc)}


def build_loan_terms(state: Dict[str, Any], documents: List[Dict[str, Any]], include_ai: bool = True) -> Dict[str, Any]:
    overrides = dict(state.get("loan_terms_overrides") or {})
    financial = state.get("financial_analysis_cache") or {}
    risk = state.get("risk_assessment_cache") or {}
    collateral = state.get("collateral_cache") or {}

    comparison = _requested_vs_policy(state, financial, collateral, overrides)
    proposed_amount = next((r["proposed"] for r in comparison if r["parameter"] == "Facility Amount"), None)
    tenor = next((r["proposed"] for r in comparison if r["parameter"] == "Tenor"), None)
    moratorium = next((r["proposed"] for r in comparison if r["parameter"] == "Moratorium"), None)
    repayment_text = overrides.get("repayment") or state.get("repayment") or "Not available"

    facility = {
        "facility_type": overrides.get("facility_type") or state.get("loan_type") or "Not available",
        "sanction_type": state.get("sanction_type") or "Not available",
        "requested_amount_cr": _cr(state.get("loan_amount_numeric") or state.get("loan_amount")),
        "proposed_amount_cr": proposed_amount,
        "purpose": state.get("loan_purpose") or state.get("purpose") or "Not available",
        "utilization_schedule": state.get("utilization_schedule") or "As per approved purpose / milestones",
        "nature": state.get("facility_nature") or "Not available",
        "sub_limit": state.get("sub_limit") or "Not available",
    }
    repayment = {
        "type": repayment_text,
        "tenor_months": tenor,
        "moratorium_months": moratorium,
        "repayment_period_months": max(0, tenor - moratorium) if tenor is not None and moratorium is not None else None,
        "interest_payment": state.get("interest_payment") or "As per sanction terms",
        "estimated_installment": state.get("estimated_installment") or "Not calculated in POC",
    }
    security = _security(collateral)
    pricing = _pricing(state, overrides)
    covenants = _covenants(financial, collateral, risk)
    pre, post = _conditions(state, risk, collateral)
    deviations = _deviations(comparison, risk)

    scored = [r for r in comparison if r["status"] != "Not Assessed"]
    overall_status = "Compliant"
    if any(r["status"] == "Deviation" for r in scored): overall_status = "Deviation / Review"
    elif any(r["status"] == "Modified" for r in scored): overall_status = "Compliant with Modifications"
    if not scored: overall_status = "Not Assessed"

    payload = {
        "cam_id": state.get("cam_id"),
        "company_name": state.get("company_name") or state.get("company") or "Borrower",
        "facility": facility,
        "comparison": comparison,
        "pricing": pricing,
        "repayment": repayment,
        "security": security,
        "covenants": covenants,
        "pre_disbursement_conditions": pre,
        "post_disbursement_conditions": post,
        "deviations": deviations,
        "overall_status": overall_status,
        "policy_basis": "POC configurable thresholds; replace with approved product/credit policy rules in production.",
        "decision_notice": "AI proposes wording only. Final facility structure, pricing, sanction conditions and deviations require authorized credit approval.",
        "overrides": overrides,
    }
    payload["commentary"] = _commentary(payload, include_ai=include_ai)
    return payload
