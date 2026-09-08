from typing import Any, Dict, List, Optional


def _first(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _to_cr(value: Any) -> Optional[float]:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return round(n / 10_000_000, 4) if abs(n) >= 100_000 else round(n, 4)


def _flat_mca(api: Dict[str, Any]) -> Dict[str, Any]:
    raw = api.get("mca_response") or {}
    if raw.get("company_name") or raw.get("cin"):
        return raw
    data = raw.get("data") if isinstance(raw, dict) else {}
    data = data or raw
    master = (data.get("masterData") or {}).get("companyData") or {}
    return {
        "company_name": _first(data.get("company"), master.get("companyName")),
        "cin": _first(data.get("cin"), master.get("cin")),
        "company_status": master.get("companyStatus"),
        "incorporation_date": master.get("dateOfIncorporation"),
        "industry": _first(master.get("industry"), master.get("principalBusinessActivity")),
        "registered_state": master.get("state"),
        "registered_city": master.get("city"),
    }


def build_loan_summary_context(state: Dict[str, Any], metrics: Dict[str, Any], ratios: Dict[str, Any], mca: Dict[str, Any], risk_flags: List[str], collateral_fields: List[Dict[str, Any]], external_data: Dict[str, Any], public_information: Dict[str, Any]) -> Dict[str, Any]:
    api = external_data.get("api") or {}
    derived = external_data.get("derived") or {}
    mock = derived.get("loan_summary_context") or {}
    mock_borrower, mock_proposal = mock.get("borrower") or {}, mock.get("proposal") or {}
    mock_fin, mock_ratios = mock.get("financials") or {}, mock.get("ratios") or {}
    mca_api = _flat_mca(api)
    proposal_api = api.get("loan_proposal") or {}
    bureau = api.get("bureau_response") or {}
    banking = api.get("internal_banking_response") or {}
    screening = api.get("sanctions_screening_response") or {}
    industry_api = api.get("industry_peer_response") or {}

    borrower = {
        "name": _first(mca.get("company_name"), mca_api.get("company_name"), state.get("company_name"), mock_borrower.get("name")),
        "constitution": _first(mock_borrower.get("constitution"), mca.get("company_type")),
        "industry": _first(mca_api.get("industry"), mock_borrower.get("industry"), industry_api.get("industry")),
        "business_vintage_years": mock_borrower.get("business_vintage_years"),
        "existing_customer": _first(banking.get("existing_customer"), mock_borrower.get("existing_customer")),
        "cin": _first(mca.get("cin"), mca_api.get("cin"), mock_borrower.get("cin")),
        "gstin": _first((api.get("gst_response") or {}).get("gstin"), mock_borrower.get("gstin"), mca.get("gstin")),
        "pan": _first((api.get("pan_response") or {}).get("pan"), mca.get("pan")),
        "location": _first(mock_borrower.get("location"), ", ".join(x for x in [mca_api.get("registered_city"), mca_api.get("registered_state")] if x)),
        "mca_status": _first(mca.get("status"), mca_api.get("company_status")),
    }
    proposal = {
        "facility_type": _first(state.get("loan_type"), proposal_api.get("facility_type"), mock_proposal.get("facility_type")),
        "requested_amount_cr": _first(_to_cr(state.get("loan_amount_numeric")), proposal_api.get("requested_amount_cr"), mock_proposal.get("requested_amount_cr")),
        "purpose": _first(state.get("loan_purpose"), proposal_api.get("purpose"), mock_proposal.get("purpose")),
        "tenure_months": _first(state.get("tenure"), proposal_api.get("tenure_months"), mock_proposal.get("tenure_months")),
        "interest_rate_pct": _first(state.get("interest_rate"), proposal_api.get("rate_pct"), mock_proposal.get("interest_rate_pct")),
        "repayment": _first(state.get("repayment"), proposal_api.get("repayment"), mock_proposal.get("repayment")),
        "rm": _first(proposal_api.get("rm"), state.get("rm_name")),
    }
    financials = {
        "latest_fy": _first(mock_fin.get("latest_fy"), (derived.get("computed_financial_metrics") or {}).get("latest_fy")),
        "revenue_cr": _first(_to_cr(metrics.get("total_revenue")), mock_fin.get("revenue_cr")),
        "ebitda_cr": _first(_to_cr(metrics.get("ebitda")), mock_fin.get("ebitda_cr")),
        "pat_cr": _first(_to_cr(metrics.get("pat")), mock_fin.get("pat_cr")),
        "net_worth_cr": _first(_to_cr(metrics.get("net_worth")), mock_fin.get("net_worth_cr")),
        "total_debt_cr": _first(_to_cr(metrics.get("total_debt")), mock_fin.get("total_debt_cr")),
        "working_capital_cr": _first(_to_cr((metrics.get("current_assets") or 0) - (metrics.get("current_liabilities") or 0)) if metrics.get("current_assets") is not None and metrics.get("current_liabilities") is not None else None, mock_fin.get("working_capital_cr")),
    }
    ratio_context = {
        "dscr": _first(ratios.get("dscr"), mock_ratios.get("dscr")),
        "icr": _first(ratios.get("interest_coverage"), ratios.get("interest_coverage_calculated"), mock_ratios.get("icr")),
        "debt_equity": _first(ratios.get("debt_equity"), mock_ratios.get("debt_equity")),
        "current_ratio": _first(ratios.get("current_ratio"), ratios.get("current_ratio_calculated"), mock_ratios.get("current_ratio")),
        "quick_ratio": _first(ratios.get("quick_ratio"), mock_ratios.get("quick_ratio")),
        "ebitda_margin_pct": _first(ratios.get("ebitda_margin"), ratios.get("ebitda_margin_calculated"), mock_ratios.get("ebitda_margin_pct")),
        "pat_margin_pct": _first(ratios.get("pat_margin"), ratios.get("pat_margin_calculated"), mock_ratios.get("pat_margin_pct")),
        "roce_pct": _first(ratios.get("roce"), mock_ratios.get("roce_pct")),
    }
    mock_credit = mock.get("credit") or {}
    credit = {
        "bureau_score": _first(bureau.get("score"), mock_credit.get("bureau_score")),
        "pd_pct": _first(bureau.get("pd_pct"), mock_credit.get("pd_pct")),
        "repayment_conduct": _first(bureau.get("repayment_conduct"), banking.get("account_conduct"), mock_credit.get("repayment_conduct")),
        "overdue_cr": _first(bureau.get("overdue_cr"), mock_credit.get("overdue_cr")),
        "average_utilisation_pct": banking.get("average_utilisation_pct"),
    }
    mock_risk, derived_risk = mock.get("risk") or {}, derived.get("risk_engine_output") or {}
    primary_risks = derived_risk.get("major_risks") or mock_risk.get("major_risks") or []
    risk = {
        "rating": _first(derived_risk.get("risk_rating"), mock_risk.get("rating")),
        "major_risks": list(dict.fromkeys([x for x in list(primary_risks) + list(risk_flags or []) if x])),
        "mitigants": derived_risk.get("mitigants") or mock_risk.get("mitigants") or [],
    }
    mock_collateral = mock.get("collateral") or {}
    collateral = {
        "gross_value_cr": mock_collateral.get("gross_value_cr"),
        "net_value_cr": mock_collateral.get("net_value_cr"),
        "coverage_ratio": mock_collateral.get("coverage_ratio"),
        "securities": mock_collateral.get("securities") or collateral_fields or [],
    }
    mock_compliance, derived_compliance = mock.get("compliance") or {}, derived.get("compliance_engine_output") or {}
    compliance = {
        "kyc": _first(derived_compliance.get("kyc_status"), mock_compliance.get("kyc")),
        "sanctions": _first(screening.get("sanctions"), mock_compliance.get("sanctions")),
        "pep": _first(screening.get("pep"), mock_compliance.get("pep")),
        "adverse_media": _first(screening.get("adverse_media"), mock_compliance.get("adverse_media")),
        "policy_observations": derived_compliance.get("policy_observations") or mock_compliance.get("policy_observations") or [],
    }
    sources = []
    if external_data.get("mock_matched"):
        sources.append({"type": "mock_api", "label": "Synthetic external API data", "status": "available"})
    if any(v is not None for v in metrics.values()):
        sources.append({"type": "documents", "label": "Uploaded financial documents", "status": "available"})
    if mca:
        sources.append({"type": "mca", "label": "MCA / FileSure", "status": "available"})
    if public_information.get("mode") != "off":
        sources.append({"type": "public_search", "label": f"Public search ({public_information.get('mode')})", "status": "available"})
    return {
        "borrower": borrower, "proposal": proposal, "financials": financials, "ratios": ratio_context,
        "credit": credit, "risk": risk, "collateral": collateral, "compliance": compliance,
        "public_information": public_information, "data_sources": sources, "data_mode": external_data.get("mode"),
    }
