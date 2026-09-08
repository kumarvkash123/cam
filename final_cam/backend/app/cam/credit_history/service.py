"""Credit History & Repayment Track Record (CAM Point 5).

The module normalizes bureau/internal-banking/document evidence, calculates
repayment/utilisation indicators deterministically, raises rule-based flags,
and optionally asks the LLM only to phrase the already calculated facts.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.cam.llm_gateway import chat as llm_chat, LLMGatewayError
from app.cam.loan_summary_service import collect_external_data


def _num(v: Any) -> Optional[float]:
    try:
        if v in (None, "", "—", "Nil", "nil"):
            return None
        if isinstance(v, str):
            text = v.replace(",", "").replace("₹", "").strip()
            m = re.search(r"-?\d+(?:\.\d+)?", text)
            if not m:
                return None
            return float(m.group())
        return float(v)
    except (TypeError, ValueError):
        return None


def _first(*values):
    for v in values:
        if v not in (None, "", [], {}):
            return v
    return None


def _field_map(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for d in documents or []:
        for k, v in (d.get("extracted_fields") or {}).items():
            if v not in (None, "", [], {}):
                out[str(k).lower().strip()] = v
    return out


def _find(fields: Dict[str, Any], *needles: str):
    for needle in needles:
        n = needle.lower()
        if n in fields:
            return fields[n]
    for k, v in fields.items():
        if any(n.lower() in k for n in needles):
            return v
    return None


def _cr(value: Any) -> Optional[float]:
    n = _num(value)
    if n is None:
        return None
    # raw extracted rupee values are converted; API mock values carrying *_cr are passed separately.
    return round(n / 10_000_000, 2) if abs(n) >= 100_000 else round(n, 2)


def _source_docs(documents: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    out = []
    for d in documents or []:
        dtype = str(d.get("doc_type") or "").lower()
        name = str(d.get("original_filename") or "")
        if any(x in dtype for x in ("bank", "bureau", "cibil", "crif", "loan", "statement")) or any(x in name.lower() for x in ("bank", "bureau", "cibil", "crif")):
            out.append({"name": name or "Credit evidence", "type": d.get("display_name") or dtype.replace("_", " ").title()})
    return out


def _facility_rows(api: Dict[str, Any], fields: Dict[str, Any]) -> List[Dict[str, Any]]:
    banking = api.get("internal_banking_response") or {}
    facilities = banking.get("facilities") or api.get("credit_facilities") or []
    rows = []
    if isinstance(facilities, list):
        for f in facilities:
            limit_cr = _first(f.get("sanctioned_limit_cr"), f.get("limit_cr"))
            outstanding_cr = _first(f.get("outstanding_cr"), f.get("utilized_cr"))
            util = _num(f.get("utilisation_pct"))
            if util is None and _num(limit_cr) not in (None, 0) and _num(outstanding_cr) is not None:
                util = round(_num(outstanding_cr) / _num(limit_cr) * 100, 1)
            rows.append({
                "lender": f.get("lender") or f.get("bank") or "Bank",
                "facility": f.get("facility_type") or f.get("type") or "Facility",
                "limit_cr": _num(limit_cr), "outstanding_cr": _num(outstanding_cr),
                "utilisation_pct": util, "status": f.get("status") or "Regular",
            })
    # If there is no detailed facility feed, show one truthful summary row when an extracted sanctioned/outstanding value exists.
    if not rows:
        limit_raw = _find(fields, "sanctioned_limit", "credit_limit", "cc_limit", "facility_limit")
        out_raw = _find(fields, "outstanding", "loan_outstanding", "utilized_amount", "utilised_amount")
        if limit_raw is not None or out_raw is not None:
            limit_cr, outstanding_cr = _cr(limit_raw), _cr(out_raw)
            util = round(outstanding_cr / limit_cr * 100, 1) if limit_cr not in (None, 0) and outstanding_cr is not None else None
            rows.append({"lender": "Extracted banking evidence", "facility": "Existing Facility", "limit_cr": limit_cr, "outstanding_cr": outstanding_cr, "utilisation_pct": util, "status": "Review source"})
    return rows


def _repayment(api: Dict[str, Any], fields: Dict[str, Any]) -> Dict[str, Any]:
    bureau = api.get("bureau_response") or {}
    banking = api.get("internal_banking_response") or {}
    hist = bureau.get("repayment_history") or banking.get("repayment_history") or []
    monthly = []
    if isinstance(hist, list):
        for x in hist[-24:]:
            dpd = _num(x.get("dpd")) or 0
            monthly.append({"period": str(x.get("period") or x.get("month") or ""), "dpd": int(dpd), "status": "30+ DPD" if dpd >= 30 else "Delayed" if dpd > 0 else "On Time"})
    total = int(_num(_first(bureau.get("total_payments_24m"), _find(fields, "total_payments_24m", "total_instalments"))) or len(monthly) or 0)
    delayed = int(_num(_first(bureau.get("delayed_payments_24m"), _find(fields, "delayed_payments", "delayed_instalments"))) or sum(1 for x in monthly if x["dpd"] > 0))
    dpd30 = int(_num(_first(bureau.get("dpd_30_events"), _find(fields, "30_dpd", "dpd_30"))) or sum(1 for x in monthly if x["dpd"] >= 30))
    max_dpd = _num(_first(bureau.get("max_dpd"), _find(fields, "max_dpd", "maximum_dpd")))
    if max_dpd is None and monthly:
        max_dpd = max(x["dpd"] for x in monthly)
    on_time = max(total - delayed, 0) if total else 0
    on_time_pct = round(on_time / total * 100, 1) if total else None
    return {"period_months": 24, "total_payments": total or None, "on_time": on_time if total else None, "delayed": delayed if total else None, "dpd_30_events": dpd30 if total or dpd30 else None, "max_dpd": max_dpd, "on_time_pct": on_time_pct, "monthly": monthly}


def _banking_conduct(api: Dict[str, Any], fields: Dict[str, Any]) -> Dict[str, Any]:
    b = api.get("internal_banking_response") or {}
    return {
        "average_monthly_credits_cr": _first(_num(b.get("average_monthly_credits_cr")), _cr(_find(fields, "average_monthly_credits", "avg_monthly_credit"))),
        "average_monthly_debits_cr": _first(_num(b.get("average_monthly_debits_cr")), _cr(_find(fields, "average_monthly_debits", "avg_monthly_debit"))),
        "average_balance_cr": _first(_num(b.get("average_balance_cr")), _cr(_find(fields, "average_balance", "avg_balance"))),
        "minimum_balance_cr": _first(_num(b.get("minimum_balance_cr")), _cr(_find(fields, "minimum_balance", "min_balance"))),
        "cheque_returns_12m": _first(_num(b.get("cheque_returns_12m")), _num(_find(fields, "cheque_returns", "cheque_return"))),
        "emi_returns_12m": _first(_num(b.get("emi_returns_12m")), _num(_find(fields, "emi_returns", "ecs_returns"))),
        "overdrawn_days": _first(_num(b.get("overdrawn_days")), _num(_find(fields, "overdrawn_days", "overdraft_days"))),
        "large_cash_deposits": _first(b.get("large_cash_deposits"), _find(fields, "large_cash_deposits")),
        "account_conduct": _first(b.get("account_conduct"), "Not available"),
    }


def _utilisation(api: Dict[str, Any], fields: Dict[str, Any]) -> Dict[str, Any]:
    b = api.get("internal_banking_response") or {}
    avg = _first(_num(b.get("average_utilisation_pct")), _num(_find(fields, "average_utilisation", "average_utilization")))
    peak = _first(_num(b.get("peak_utilisation_pct")), _num(_find(fields, "peak_utilisation", "peak_utilization")))
    over = _first(_num(b.get("overdrawn_days")), _num(_find(fields, "overdrawn_days")))
    breaches = _first(_num(b.get("limit_breaches_12m")), _num(_find(fields, "limit_breaches", "limit_breach")))
    rows = [
        {"metric": "Average Utilisation", "value": avg, "display": f"{avg:.0f}%" if avg is not None else "—", "benchmark": "≤ 75%", "status": "Pass" if avg is not None and avg <= 75 else "Watch" if avg is not None else "Unavailable"},
        {"metric": "Peak Utilisation", "value": peak, "display": f"{peak:.0f}%" if peak is not None else "—", "benchmark": "≤ 90%", "status": "Pass" if peak is not None and peak <= 90 else "Watch" if peak is not None else "Unavailable"},
        {"metric": "Overdrawn Days", "value": over, "display": f"{over:.0f}" if over is not None else "—", "benchmark": "≤ 15", "status": "Pass" if over is not None and over <= 15 else "Watch" if over is not None else "Unavailable"},
        {"metric": "Limit Breaches (12M)", "value": breaches, "display": f"{breaches:.0f}" if breaches is not None else "—", "benchmark": "0", "status": "Pass" if breaches == 0 else "Watch" if breaches is not None else "Unavailable"},
    ]
    return {"average_utilisation_pct": avg, "peak_utilisation_pct": peak, "overdrawn_days": over, "limit_breaches_12m": breaches, "rows": rows}


def _flags(bureau, repayment, conduct, utilisation) -> List[Dict[str, str]]:
    flags: List[Dict[str, str]] = []
    overdue = _num(bureau.get("overdue_cr"))
    if overdue in (0, 0.0): flags.append({"level":"good", "text":"No current overdue reported in available bureau data."})
    elif overdue is not None: flags.append({"level":"risk", "text":f"Current overdue of ₹{overdue:.2f} Cr requires review."})
    if repayment.get("dpd_30_events") == 0: flags.append({"level":"good", "text":"No 30+ DPD event identified in the available repayment history."})
    if repayment.get("on_time_pct") is not None:
        level = "good" if repayment["on_time_pct"] >= 90 else "watch"
        flags.append({"level":level, "text":f"On-time repayment rate is {repayment['on_time_pct']:.0f}% for the analysed period."})
    peak = utilisation.get("peak_utilisation_pct")
    if peak is not None and peak > 90: flags.append({"level":"watch", "text":f"Peak working-capital utilisation reached {peak:.0f}%, indicating tight headroom."})
    cheque = conduct.get("cheque_returns_12m")
    if cheque is not None and cheque > 0: flags.append({"level":"watch", "text":f"{int(cheque)} cheque return(s) observed in the available 12-month banking data."})
    if bureau.get("npa_flag") is False: flags.append({"level":"good", "text":"No NPA flag reported by the available bureau source."})
    if not flags: flags.append({"level":"info", "text":"Credit evidence is incomplete; obtain bureau and banking-conduct data before final assessment."})
    return flags


def _deterministic_commentary(company: str, bureau, repayment, conduct, utilisation, flags) -> str:
    bits = []
    score = _num(bureau.get("score"))
    if score is not None: bits.append(f"The available commercial bureau score is {score:.0f}.")
    if repayment.get("on_time") is not None and repayment.get("total_payments"):
        bits.append(f"{repayment['on_time']} of {repayment['total_payments']} analysed scheduled payments were on time, with maximum DPD of {repayment.get('max_dpd') if repayment.get('max_dpd') is not None else 'not available'} days.")
    overdue = _num(bureau.get("overdue_cr"))
    if overdue == 0: bits.append("No current overdue is reported in the available bureau feed.")
    avg = utilisation.get("average_utilisation_pct")
    if avg is not None: bits.append(f"Average working-capital utilisation is {avg:.0f}%.")
    if conduct.get("cheque_returns_12m") is not None: bits.append(f"Cheque returns in the available 12-month banking data: {int(conduct['cheque_returns_12m'])}.")
    return " ".join(bits) if bits else f"Insufficient structured credit-history evidence is currently available for {company}."


def _ai_commentary(base: str, payload: Dict[str, Any]) -> Dict[str, str]:
    try:
        content = llm_chat([
            {"role":"system","content":"You are a bank CAM analyst. Write one concise Credit History & Repayment Track Record paragraph using ONLY supplied facts. Do not calculate, infer, invent, or label missing data as clear. Mention both positive conduct and material watch items. Max 130 words."},
            {"role":"user","content":json.dumps(payload, ensure_ascii=False)},
        ], temperature=0.1)
        return {"source":"ai_generated", "text":str(content).strip(), "error":""}
    except (LLMGatewayError, TypeError, ValueError) as exc:
        return {"source":"deterministic", "text":base, "error":str(exc)}


def build_credit_history(state: Dict[str, Any], documents: List[Dict[str, Any]], include_ai: bool = True) -> Dict[str, Any]:
    external = collect_external_data(state)
    api = external.get("api") or {}
    derived = external.get("derived") or {}
    fields = _field_map(documents)
    bureau = dict(api.get("bureau_response") or {})
    banking = dict(api.get("internal_banking_response") or {})
    mock_credit = ((derived.get("loan_summary_context") or {}).get("credit") or {})
    for key, val in mock_credit.items():
        bureau.setdefault(key, val)

    # Supplement bureau values from uploaded evidence without overwriting API values.
    bureau.setdefault("score", _num(_find(fields, "bureau_score", "cibil_score", "commercial_credit_score")))
    bureau.setdefault("overdue_cr", _cr(_find(fields, "current_overdue", "overdue_amount")))
    bureau.setdefault("max_dpd", _num(_find(fields, "max_dpd", "maximum_dpd")))
    bureau.setdefault("npa_flag", _find(fields, "npa_flag", "npa_status"))

    facilities = _facility_rows(api, fields)
    repayment = _repayment(api, fields)
    conduct = _banking_conduct(api, fields)
    utilisation = _utilisation(api, fields)
    flags = _flags(bureau, repayment, conduct, utilisation)

    sanctioned = round(sum((x.get("limit_cr") or 0) for x in facilities), 2) if facilities else None
    outstanding = round(sum((x.get("outstanding_cr") or 0) for x in facilities), 2) if facilities else None
    # If no facility rows, retain bureau aggregate if explicitly provided.
    if outstanding is None:
        outstanding = _num(_first(bureau.get("total_outstanding_cr"), bureau.get("outstanding_cr")))
    overdue = _num(bureau.get("overdue_cr"))
    score = _num(bureau.get("score"))
    score_status = "Good" if score is not None and score >= 700 else "Watch" if score is not None and score >= 650 else "Review" if score is not None else "Unavailable"
    max_dpd = repayment.get("max_dpd")
    dpd_status = "Low" if max_dpd is not None and max_dpd <= 30 else "Watch" if max_dpd is not None and max_dpd <= 90 else "High" if max_dpd is not None else "Unavailable"

    bureau_summary = [
        {"parameter":"Commercial Credit Score", "value": score, "display": f"{score:.0f}" if score is not None else "—", "status": score_status},
        {"parameter":"Active Credit Facilities", "value": bureau.get("active_facilities"), "display": str(bureau.get("active_facilities") if bureau.get("active_facilities") is not None else len([x for x in facilities if str(x.get('status')).lower() != 'closed']) or "—"), "status":""},
        {"parameter":"Closed Credit Facilities", "value": bureau.get("closed_facilities"), "display": str(bureau.get("closed_facilities") if bureau.get("closed_facilities") is not None else "—"), "status":""},
        {"parameter":"Recent Credit Enquiries", "value": bureau.get("recent_enquiries"), "display": str(bureau.get("recent_enquiries") if bureau.get("recent_enquiries") is not None else "—"), "status":""},
        {"parameter":"Current Overdue", "value": overdue, "display": "Nil" if overdue == 0 else f"₹ {overdue:.2f} Cr" if overdue is not None else "—", "status":"Clear" if overdue == 0 else "Review" if overdue is not None else ""},
        {"parameter":"SMA / NPA / Restructuring", "value": bureau.get("npa_flag"), "display": "Nil" if bureau.get("npa_flag") is False else str(bureau.get("npa_flag") if bureau.get("npa_flag") not in (None, "") else "—"), "status":"Clear" if bureau.get("npa_flag") is False else ""},
        {"parameter":"Suit Filed / Wilful Default", "value": bureau.get("wilful_default"), "display": str(bureau.get("wilful_default") if bureau.get("wilful_default") not in (None, "") else "—"), "status":""},
    ]

    company = state.get("company_name") or state.get("company") or "Borrower"
    base = _deterministic_commentary(company, bureau, repayment, conduct, utilisation, flags)
    commentary = {"source":"deterministic", "text":base, "error":""}
    if include_ai:
        commentary = _ai_commentary(base, {"company":company,"bureau":bureau_summary,"repayment":repayment,"banking_conduct":conduct,"utilisation":utilisation,"risk_flags":flags})

    return {
        "company_name": company, "cam_id": state.get("cam_id"),
        "kpis": {
            "bureau_score": score, "bureau_score_status": score_status,
            "sanctioned_exposure_cr": sanctioned, "outstanding_cr": outstanding,
            "current_overdue_cr": overdue, "max_dpd": max_dpd, "max_dpd_status": dpd_status,
            "facility_count": len(facilities),
        },
        "facilities": facilities,
        "repayment": repayment,
        "banking_conduct": conduct,
        "bureau_summary": bureau_summary,
        "utilisation": utilisation,
        "risk_flags": flags,
        "commentary": commentary,
        "sources": _source_docs(documents),
        "data_mode": external.get("mode"),
        "methodology": "Repayment, overdue and utilisation indicators are calculated deterministically from available bureau, banking and uploaded-document evidence. AI is used only to phrase the commentary.",
    }
