"""Risk Assessment & Mitigation (CAM Point 6).

This module consolidates outputs already calculated by the financial-analysis,
credit-history, borrower and business-overview modules. Risk detection,
threshold comparisons and scoring are deterministic. The LLM may only phrase
an already-built risk register and mitigation set; it never decides approval.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from app.cam.llm_gateway import chat as llm_chat, LLMGatewayError


SEVERITY_SCORE = {"Low": 25, "Moderate": 55, "High": 80, "Critical": 100}
SEVERITY_ORDER = {"Low": 1, "Moderate": 2, "High": 3, "Critical": 4}


def _num(v: Any) -> Optional[float]:
    try:
        if v in (None, "", "—", "N/A", "Not available"):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _severity_from_status(status: str) -> str:
    s = str(status or "").strip().lower()
    if s in ("deviation", "fail", "failed", "high", "stressed", "risk", "concern"):
        return "High"
    if s in ("watch", "review", "moderate", "needs review"):
        return "Moderate"
    return "Low"


def _risk(category: str, area: str, observation: str, severity: str,
          source: str, mitigation: List[str], indicator: str = "",
          actual: Any = None, threshold: str = "", likelihood: str = "Medium",
          impact: str = "Medium") -> Dict[str, Any]:
    return {
        "category": category,
        "risk_area": area,
        "observation": observation,
        "severity": severity,
        "source": source,
        "mitigation": mitigation[:3],
        "indicator": indicator,
        "actual": actual,
        "threshold": threshold,
        "likelihood": likelihood,
        "impact": impact,
    }


def _financial_risks(financial: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    risks: List[Dict[str, Any]] = []
    triggers: List[Dict[str, Any]] = []
    positives: List[str] = []

    for row in financial.get("ratios") or []:
        value = row.get("value")
        status = row.get("status") or "Unavailable"
        triggers.append({
            "indicator": row.get("label") or row.get("key"),
            "actual": row.get("display_value") or "—",
            "threshold": row.get("benchmark") or "—",
            "result": status,
            "source": "Financial Analysis",
        })
        if value is None:
            continue
        sev = _severity_from_status(status)
        if sev != "Low":
            area = row.get("label") or "Financial indicator"
            risks.append(_risk(
                "Financial Risk", area,
                f"{area} is {row.get('display_value')} against benchmark {row.get('benchmark')}.",
                sev, "Financial Analysis", [
                    "Review the driver of the threshold breach with the credit officer.",
                    "Set a monitoring covenant appropriate to the indicator.",
                    "Reassess exposure or repayment structure if the weakness persists.",
                ], area, row.get("display_value"), row.get("benchmark"),
                "Medium", "High" if sev == "High" else "Medium"
            ))
        elif row.get("key") in ("dscr", "interest_coverage", "current_ratio", "debt_equity"):
            positives.append(f"{row.get('label')} at {row.get('display_value')} is within the configured benchmark.")

    stresses = financial.get("stress_testing") or []
    severe = next((x for x in stresses if str(x.get("scenario", "")).lower().startswith("severe")), None)
    if severe:
        dscr = _num(severe.get("dscr"))
        if dscr is not None:
            result = "Deviation" if dscr < 1.0 else "Watch" if dscr < 1.2 else "Pass"
            triggers.append({"indicator":"DSCR (Severe Stress)", "actual":f"{dscr:.2f}x", "threshold":"≥ 1.00x", "result":result, "source":"Financial Stress Test"})
            if dscr < 1.2:
                sev = "High" if dscr < 1.0 else "Moderate"
                risks.append(_risk(
                    "Financial Risk", "Stress Repayment Capacity",
                    f"Severe-stress DSCR declines to {dscr:.2f}x.", sev,
                    "Financial Stress Test", [
                        "Consider a debt-service reserve / liquidity buffer subject to policy.",
                        "Increase frequency of cash-flow and covenant monitoring.",
                        "Review tenor, amortisation or exposure if downside resilience is insufficient.",
                    ], "Severe Stress DSCR", f"{dscr:.2f}x", "≥ 1.00x",
                    "Medium", "High"
                ))
            else:
                positives.append(f"Severe-stress DSCR remains at {dscr:.2f}x.")

    movements = financial.get("material_movements") or []
    rev = next((x for x in movements if str(x.get("metric", "")).lower() == "revenue"), None)
    rec = next((x for x in movements if "receiv" in str(x.get("metric", "")).lower()), None)
    if rev and rec and _num(rev.get("change_pct")) is not None and _num(rec.get("change_pct")) is not None:
        gap = _num(rec.get("change_pct")) - _num(rev.get("change_pct"))
        if gap >= 15:
            risks.append(_risk(
                "Working Capital Risk", "Receivable Growth",
                f"Receivables increased {_num(rec.get('change_pct')):.1f}% versus revenue growth of {_num(rev.get('change_pct')):.1f}%.",
                "Moderate", "Financial Analysis", [
                    "Monitor debtor ageing and collection efficiency monthly.",
                    "Review concentration in major debtors and overdue receivables.",
                    "Link drawing-power monitoring to eligible receivables where applicable.",
                ], "Receivable growth gap", f"{gap:.1f} pp", "Review if materially above revenue growth", "Medium", "Medium"
            ))
    return risks, triggers, positives


def _credit_risks(credit: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    risks: List[Dict[str, Any]] = []
    triggers: List[Dict[str, Any]] = []
    positives: List[str] = []
    k = credit.get("kpis") or {}
    util = credit.get("utilisation") or {}

    max_dpd = _num(k.get("max_dpd"))
    if max_dpd is not None:
        result = "Pass" if max_dpd <= 30 else "Watch" if max_dpd <= 60 else "Deviation"
        triggers.append({"indicator":"Max DPD (Last 24M)", "actual":f"{max_dpd:.0f} days", "threshold":"≤ 30 days", "result":result, "source":"Credit History"})
        if max_dpd > 30:
            risks.append(_risk("Repayment Risk", "Historical Delinquency", f"Maximum DPD is {max_dpd:.0f} days.", "High" if max_dpd > 60 else "Moderate", "Credit History", ["Review cause and cure of past delays.", "Increase repayment monitoring frequency.", "Consider tighter covenants / account-routing controls where appropriate."], "Max DPD", f"{max_dpd:.0f} days", "≤ 30 days", "Medium", "High"))
        else:
            positives.append(f"Maximum DPD of {max_dpd:.0f} days is within the configured review threshold.")

    overdue = _num(k.get("current_overdue_cr"))
    if overdue is not None:
        triggers.append({"indicator":"Current Overdue", "actual":"₹ 0" if overdue == 0 else f"₹ {overdue:.2f} Cr", "threshold":"= 0", "result":"Pass" if overdue == 0 else "Deviation", "source":"Credit History"})
        if overdue > 0:
            risks.append(_risk("Repayment Risk", "Current Overdue", f"Current overdue is ₹ {overdue:.2f} Cr.", "High", "Credit History", ["Obtain overdue clearance / regularisation evidence.", "Validate repayment source before further exposure.", "Escalate per applicable delinquency policy."], "Current Overdue", f"₹ {overdue:.2f} Cr", "= 0", "High", "High"))
        else:
            positives.append("No current overdue is reported in the available credit-history evidence.")

    peak = _num(util.get("peak_utilisation_pct"))
    if peak is not None:
        triggers.append({"indicator":"Peak CC Utilisation", "actual":f"{peak:.0f}%", "threshold":"≤ 90%", "result":"Pass" if peak <= 90 else "Watch", "source":"Credit History"})
        if peak > 90:
            risks.append(_risk("Working Capital Risk", "Working Capital Dependence", f"Peak working-capital utilisation reached {peak:.0f}%.", "Moderate" if peak <= 100 else "High", "Credit History", ["Obtain monthly stock and receivable statements.", "Review drawing power and utilisation trend monthly.", "Route major operating receipts through the lending-bank account where applicable."], "Peak Utilisation", f"{peak:.0f}%", "≤ 90%", "Medium", "Medium"))

    conduct = credit.get("banking_conduct") or {}
    cheque = _num(conduct.get("cheque_returns_12m"))
    if cheque is not None:
        triggers.append({"indicator":"Cheque Returns (12M)", "actual":f"{cheque:.0f}", "threshold":"≤ 2", "result":"Pass" if cheque <= 2 else "Watch", "source":"Bank Statement Analysis"})
        if cheque > 2:
            risks.append(_risk("Repayment Risk", "Cheque / Payment Returns", f"{cheque:.0f} cheque returns were identified in the available 12-month banking evidence.", "Moderate" if cheque <= 5 else "High", "Bank Statement Analysis", ["Review return reasons and recurrence.", "Monitor account conduct monthly.", "Seek operating-account discipline / routing as appropriate."], "Cheque Returns", f"{cheque:.0f}", "≤ 2", "Medium", "Medium"))

    for f in credit.get("risk_flags") or []:
        if str(f.get("level")).lower() == "good" and f.get("text"):
            positives.append(str(f["text"]))
    return risks, triggers, positives


def _business_risks(business: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    risks: List[Dict[str, Any]] = []
    positives: List[str] = []
    for item in business.get("business_risks") or []:
        text = item.get("text") if isinstance(item, dict) else str(item)
        if text:
            risks.append(_risk("Business Risk", "Business / Market Observation", text, "Moderate", "Business Overview", ["Validate the identified business risk with current operating evidence.", "Define a borrower-specific monitoring trigger.", "Capture a management action / mitigating factor in the sanction conditions."], likelihood="Medium", impact="Medium"))
    for item in business.get("strengths") or []:
        text = item.get("text") if isinstance(item, dict) else str(item)
        if text:
            positives.append(text)
    return risks, positives



def _collateral_risks(collateral: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    risks: List[Dict[str, Any]] = []
    triggers: List[Dict[str, Any]] = []
    positives: List[str] = []
    if not collateral:
        return risks, triggers, positives
    c = collateral.get("coverage") or collateral.get("summary") or {}
    ratio = _num(c.get("coverage_ratio"))
    threshold = _num(c.get("policy_threshold"))
    if ratio is not None and threshold is not None:
        result = "Pass" if ratio >= threshold else "Deviation"
        triggers.append({"indicator":"Security Coverage","actual":f"{ratio:.2f}x","threshold":f"≥ {threshold:.2f}x","result":result,"source":"Collateral Analysis"})
        if ratio < threshold:
            risks.append(_risk("Collateral Risk","Security Coverage",f"Security coverage of {ratio:.2f}x is below the configured threshold of {threshold:.2f}x.","High","Collateral Analysis",["Obtain additional eligible security or reduce exposure subject to policy.","Seek delegated approval if a policy deviation is proposed.","Recalculate coverage after valuation/legal adjustments."],"Security Coverage",f"{ratio:.2f}x",f"≥ {threshold:.2f}x","Medium","High"))
        else:
            positives.append(f"Security coverage of {ratio:.2f}x meets the configured threshold of {threshold:.2f}x.")
    for v in collateral.get("valuations") or []:
        if str(v.get("status")).lower() == "revaluation required":
            risks.append(_risk("Collateral Risk","Valuation Age",f"Valuation for {v.get('security')} is {v.get('age_months')} months old and requires review.","Moderate","Collateral Analysis",["Obtain a fresh valuation from an approved valuer before reliance/disbursement.","Recompute eligible value and coverage after revaluation."],"Valuation Age",f"{v.get('age_months')} months","Configured validity review","Medium","Medium"))
    for check in collateral.get("validation_checks") or []:
        status = str(check.get("status") or "").lower()
        name = str(check.get("check") or "Collateral validation")
        if status in ("review","expired"):
            sev = "High" if status == "expired" or "charge" in name.lower() and "mca" in name.lower() else "Moderate"
            risks.append(_risk("Collateral Risk",name,f"{name}: {check.get('detail') or 'requires verification'}.",sev,"Collateral Analysis",["Obtain documentary/legal verification before relying on the security.","Record the resolution and evidence in the CAM before disbursement."],name,check.get("status"),"Verified / acceptable","Medium","High" if sev=="High" else "Medium"))
    return risks, triggers, positives


def _industry_peer_risks(industry_peer: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    risks: List[Dict[str, Any]] = []
    positives: List[str] = []
    for row in industry_peer.get("peer_comparison") or []:
        position = str(row.get("position") or "")
        if position == "Weaker":
            risks.append(_risk(
                "Industry/Market Risk",
                f"Relative {row.get('metric')}",
                f"{row.get('metric')} ({row.get('borrower')}) is weaker than the available {str(row.get('benchmark_label') or 'benchmark').lower()} ({row.get('benchmark')}).",
                "Moderate", "Industry & Peer Analysis",
                [
                    "Reflect the relative weakness in monitoring and covenant design.",
                    "Track the indicator against updated peer/industry evidence during review.",
                    "Escalate if deterioration becomes material to repayment capacity.",
                ],
                row.get("metric") or "Peer metric", row.get("borrower"), row.get("benchmark"),
                "Medium", "Medium"
            ))
        elif position == "Better":
            positives.append(f"{row.get('metric')} is better than the available {str(row.get('benchmark_label') or 'benchmark').lower()}.")
    outlook = str((industry_peer.get("summary") or {}).get("overall_outlook") or "")
    if outlook == "Weak":
        risks.append(_risk(
            "Industry/Market Risk", "Industry Outlook",
            "Available industry evidence indicates a weak / contracting outlook.",
            "Moderate", "Industry & Peer Analysis",
            ["Apply closer sector monitoring.", "Review downside sensitivity and assumptions during periodic credit review.", "Consider tighter information covenants where appropriate."],
            "Industry Outlook", outlook, "Stable / Positive", "Medium", "Medium"
        ))
    elif outlook in ("Positive", "Stable"):
        positives.append(f"Available industry outlook is assessed as {outlook.lower()}.")
    for item in industry_peer.get("risks") or []:
        text = str(item or "").strip()
        if text and not any(text == r.get("observation") for r in risks):
            risks.append(_risk(
                "Industry/Market Risk", "Market / Peer Observation", text, "Moderate",
                "Industry & Peer Analysis",
                ["Monitor the identified market factor during credit review.", "Reflect material market weakness in covenants or exposure review where required."],
                likelihood="Medium", impact="Medium"
            ))
    return risks, positives


def _policy_triggers(state: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    triggers: List[Dict[str, Any]] = []
    risks: List[Dict[str, Any]] = []
    for p in state.get("policy_checks") or []:
        if not isinstance(p, dict):
            continue
        result = str(p.get("status") or p.get("result") or "Review")
        triggers.append({
            "indicator": p.get("rule") or p.get("field") or "Policy check",
            "actual": p.get("actual") or p.get("value") or "—",
            "threshold": p.get("threshold") or p.get("policy_value") or "See policy",
            "result": result,
            "source": p.get("source") or "Policy Check",
        })
        if result.lower() in ("deviation", "non compliant", "non-compliant", "fail", "failed"):
            risks.append(_risk("Policy Risk", "Policy Deviation", str(p.get("observation") or p.get("rule") or "A policy deviation requires review."), "High", p.get("source") or "Policy Check", [str(p.get("mitigation") or "Obtain delegated approval or align the proposal with policy."), "Document rationale and approving authority.", "Track compliance with any approved deviation condition."], p.get("field") or "Policy", p.get("actual"), str(p.get("threshold") or "See policy"), "Medium", "High"))
    return triggers, risks


def _category_summary(risks: List[Dict[str, Any]], business_available: bool, policy_available: bool, collateral_available: bool=False, industry_available: bool=False) -> List[Dict[str, Any]]:
    categories = [
        "Financial Risk", "Repayment Risk", "Working Capital Risk", "Business Risk",
        "Industry/Market Risk", "Management Risk", "Collateral Risk", "Compliance Risk",
        "Concentration Risk", "Policy Risk",
    ]
    out = []
    for category in categories:
        matches = [r for r in risks if r["category"] == category]
        if matches:
            sev = max((r["severity"] for r in matches), key=lambda x: SEVERITY_ORDER.get(x, 0))
            available = True
        else:
            # Only categories supported by currently-available upstream modules are safe to call Low.
            available = category in ("Financial Risk", "Repayment Risk", "Working Capital Risk") or (category == "Business Risk" and business_available) or (category == "Industry/Market Risk" and industry_available) or (category == "Collateral Risk" and collateral_available) or (category == "Policy Risk" and policy_available)
            sev = "Low" if available else "Not Assessed"
        out.append({"category": category, "severity": sev, "score": SEVERITY_SCORE.get(sev), "available": available})
    return out


def _overall(categories: List[Dict[str, Any]], risks: List[Dict[str, Any]], triggers: List[Dict[str, Any]]) -> Dict[str, Any]:
    assessed = [c for c in categories if c.get("available") and c.get("score") is not None]
    score = round(sum(c["score"] for c in assessed) / len(assessed)) if assessed else None
    high = sum(1 for r in risks if r.get("severity") in ("High", "Critical"))
    moderate = sum(1 for r in risks if r.get("severity") == "Moderate")
    deviations = sum(1 for t in triggers if str(t.get("result", "")).lower() in ("deviation", "fail", "failed", "non compliant", "non-compliant"))
    if score is None:
        rating = "Not Assessed"
    elif high >= 2 or score >= 75:
        rating = "High"
    elif high >= 1 or moderate >= 1 or score >= 45:
        rating = "Moderate"
    else:
        rating = "Low"
    return {"score": score, "rating": rating, "high": high, "moderate": moderate, "low": sum(1 for c in assessed if c["severity"] == "Low"), "policy_deviations": deviations, "assessed_categories": len(assessed)}


def _base_commentary(company: str, overall: Dict[str, Any], risks: List[Dict[str, Any]], positives: List[str]) -> str:
    if overall.get("score") is None:
        return f"The overall credit risk for {company} cannot yet be rated because the required upstream risk evidence is incomplete."
    lead = f"Overall credit risk is assessed as {overall['rating']} ({overall['score']}/100) based only on the currently assessed categories."
    concerns = [r["observation"] for r in risks if r["severity"] in ("High", "Moderate")][:3]
    pos = positives[:2]
    parts = [lead]
    if pos:
        parts.append("Positive factors include " + " ".join(pos))
    if concerns:
        parts.append("Key concerns are " + " ".join(concerns))
    parts.append("The rating is decision support only; final credit judgement and mitigation acceptance remain with the authorised credit officer.")
    return " ".join(parts)


def _ai_commentary(base: str, payload: Dict[str, Any]) -> Dict[str, str]:
    try:
        content = llm_chat([
            {"role": "system", "content": "You are a bank CAM risk analyst. Use ONLY supplied deterministic facts. Do not create a new score, threshold, risk, mitigation or approval recommendation. Return JSON with one field commentary containing one concise paragraph (max 170 words). Explicitly note that final judgement remains with the credit officer."},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ], temperature=0.1, response_format={"type": "json_object"})
        parsed = json.loads(content)
        text = str(parsed.get("commentary") or "").strip()
        if text:
            return {"source":"ai_generated", "text":text, "error":""}
    except (LLMGatewayError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {"source":"deterministic", "text":base, "error":str(exc)}
    return {"source":"deterministic", "text":base, "error":"AI commentary unavailable."}


def build_risk_assessment(state: Dict[str, Any], documents: List[Dict[str, Any]], include_ai: bool = True) -> Dict[str, Any]:
    financial = state.get("financial_analysis_cache") or {}
    credit = state.get("credit_history_cache") or {}
    business = state.get("business_overview_cache") or {}
    collateral = state.get("collateral_cache") or {}
    industry_peer = state.get("industry_peer_cache") or {}

    risks: List[Dict[str, Any]] = []
    triggers: List[Dict[str, Any]] = []
    positives: List[str] = []

    r, t, p = _financial_risks(financial); risks += r; triggers += t; positives += p
    r, t, p = _credit_risks(credit); risks += r; triggers += t; positives += p
    r, p = _business_risks(business); risks += r; positives += p
    r, t, p = _collateral_risks(collateral); risks += r; triggers += t; positives += p
    r, p = _industry_peer_risks(industry_peer); risks += r; positives += p
    t, r = _policy_triggers(state); triggers += t; risks += r

    # Remove repeated observations/positives while preserving evidence order.
    seen = set(); unique_risks = []
    for r in risks:
        key = (r.get("category"), r.get("risk_area"), r.get("observation"))
        if key not in seen:
            seen.add(key); unique_risks.append(r)
    risks = unique_risks
    positives = list(dict.fromkeys(x for x in positives if x))[:8]

    categories = _category_summary(risks, bool(business), bool(state.get("policy_checks")), bool(collateral), bool(industry_peer))
    overall = _overall(categories, risks, triggers)
    company = state.get("company_name") or state.get("company") or "Borrower"
    base = _base_commentary(company, overall, risks, positives)
    commentary = {"source":"deterministic", "text":base, "error":""}
    if include_ai:
        commentary = _ai_commentary(base, {"company":company, "overall":overall, "categories":categories, "key_risks":risks[:8], "policy_thresholds":triggers[:12], "positive_factors":positives})

    sources = []
    for name, cache in (("Financial Analysis", financial), ("Credit History", credit), ("Business Overview", business), ("Collateral Analysis", collateral), ("Industry & Peer Analysis", industry_peer)):
        if cache:
            sources.append({"name":name, "type":"Upstream CAM module"})
    if state.get("policy_sources"):
        sources.append({"name":"Uploaded Bank Policies", "type":"Policy evidence"})

    return {
        "company_name": company,
        "cam_id": state.get("cam_id"),
        "overall": overall,
        "categories": categories,
        "risks": risks,
        "policy_triggers": triggers,
        "positive_factors": positives,
        "key_concerns": [r["observation"] for r in risks if r["severity"] in ("High", "Moderate")][:8],
        "commentary": commentary,
        "sources": sources,
        "methodology": "Risk detection, threshold comparison and score aggregation are deterministic and use cached upstream CAM outputs. AI is used only to phrase commentary. Unavailable categories are shown as Not Assessed and are excluded from the overall score.",
        "decision_notice": "Decision-support output only. Final credit decision, risk acceptance and sanction conditions require authorised human review.",
    }
