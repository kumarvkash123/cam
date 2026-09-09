from typing import Any, Dict, List, Optional

from app.cam.verification.synthetic_provider import LACTOSE_CIN, lactose_company_master


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


def build_loan_summary_context(state: Dict[str, Any], metrics: Dict[str, Any], ratios: Dict[str, Any], mca: Dict[str, Any], risk_flags: List[str], collateral_fields: List[Dict[str, Any]], external_data: Dict[str, Any], public_information: Dict[str, Any], document_proposal: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    api = external_data.get("api") or {}
    derived = external_data.get("derived") or {}
    mock = derived.get("loan_summary_context") or {}
    mock_borrower, mock_proposal = mock.get("borrower") or {}, mock.get("proposal") or {}
    mock_fin, mock_ratios = mock.get("financials") or {}, mock.get("ratios") or {}
    mca_api = _flat_mca(api)
    proposal_api = api.get("loan_proposal") or {}
    document_proposal = document_proposal or {}
    bureau = api.get("bureau_response") or {}
    banking = api.get("internal_banking_response") or {}
    screening = api.get("sanctions_screening_response") or {}
    industry_api = api.get("industry_peer_response") or {}

    # Lactose POC private verification: use clearly-labelled synthetic values only
    # when genuine bank/bureau/collateral integrations are unavailable.
    state_cin = _first(mca.get("cin"), mca_api.get("cin"), state.get("cin"))
    lactose_poc = {}
    if str(state_cin or "").upper() == LACTOSE_CIN or "lactose" in str(state.get("company_name") or "").lower():
        lactose_poc = (lactose_company_master().get("poc_additional_verification") or {})

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
    # Source priority for proposal terms:
    # user-confirmed state > uploaded loan application > external proposal API > mock POC.
    # The uploaded document amount is already normalized to crore by its
    # document-specific extractor; do not send it through _to_cr again.
    proposal = {
        "facility_type": _first(state.get("loan_type"), document_proposal.get("facility_type"), proposal_api.get("facility_type"), mock_proposal.get("facility_type")),
        "requested_amount_cr": _first(_to_cr(state.get("loan_amount_numeric")), document_proposal.get("requested_amount_cr"), proposal_api.get("requested_amount_cr"), mock_proposal.get("requested_amount_cr")),
        "purpose": _first(state.get("loan_purpose"), document_proposal.get("purpose"), proposal_api.get("purpose"), mock_proposal.get("purpose")),
        "tenure_months": _first(state.get("tenure"), document_proposal.get("tenure_months"), proposal_api.get("tenure_months"), mock_proposal.get("tenure_months")),
        "interest_rate_pct": _first(state.get("interest_rate"), document_proposal.get("interest_rate_pct"), proposal_api.get("rate_pct"), mock_proposal.get("interest_rate_pct")),
        "pricing": _first(document_proposal.get("pricing"), proposal_api.get("pricing")),
        "repayment": _first(state.get("repayment"), document_proposal.get("repayment"), proposal_api.get("repayment"), mock_proposal.get("repayment")),
        "moratorium_months": document_proposal.get("moratorium_months"),
        "processing_fee_pct": document_proposal.get("processing_fee_pct"),
        "primary_security": document_proposal.get("primary_security"),
        "collateral": document_proposal.get("collateral"),
        "proposal_source": document_proposal.get("source_document"),
        "rm": _first(proposal_api.get("rm"), state.get("rm_name")),
    }
    financials = {
        "latest_fy": _first(metrics.get("latest_fy"), mock_fin.get("latest_fy"), (derived.get("computed_financial_metrics") or {}).get("latest_fy")),
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
    poc_bureau = lactose_poc.get("credit_bureau") or {}
    poc_banking = lactose_poc.get("banking_conduct") or {}
    credit = {
        "bureau_score": _first(bureau.get("score"), mock_credit.get("bureau_score"), poc_bureau.get("company_score")),
        "pd_pct": _first(bureau.get("pd_pct"), mock_credit.get("pd_pct")),
        "repayment_conduct": _first(bureau.get("repayment_conduct"), banking.get("account_conduct"), mock_credit.get("repayment_conduct"), poc_banking.get("interest_servicing")),
        "overdue_cr": _first(bureau.get("overdue_cr"), mock_credit.get("overdue_cr"), 0 if poc_banking.get("overdue_days") == 0 else None),
        "average_utilisation_pct": _first(banking.get("average_utilisation_pct"), 88.4 if poc_banking else None),
        "maximum_utilisation_pct": _first(banking.get("maximum_utilisation_pct"), 96.2 if poc_banking else None),
        "sma_status": _first(banking.get("sma_status"), poc_banking.get("sma_status")),
        "account_status": _first(banking.get("account_status"), poc_banking.get("account_status")),
        "cheque_returns": _first(banking.get("cheque_returns"), 0 if poc_banking else None),
        "existing_exposure_cr": banking.get("existing_exposure_cr"),
        "source": "synthetic_poc" if poc_banking or poc_bureau else ("api" if bureau or banking else None),
        "synthetic": bool(poc_banking or poc_bureau),
    }
    mock_risk, derived_risk = mock.get("risk") or {}, derived.get("risk_engine_output") or {}
    primary_risks = derived_risk.get("major_risks") or mock_risk.get("major_risks") or []
    risk = {
        "rating": _first(derived_risk.get("risk_rating"), mock_risk.get("rating")),
        "major_risks": list(dict.fromkeys([x for x in list(primary_risks) + list(risk_flags or []) if x])),
        "mitigants": derived_risk.get("mitigants") or mock_risk.get("mitigants") or [],
    }
    mock_collateral = mock.get("collateral") or {}
    poc_collateral = lactose_poc.get("collateral") or {}
    # Synthetic valuation amounts are POC-only and kept separate from genuine evidence.
    poc_gross = 82.0 if poc_collateral else None
    poc_net = 69.7 if poc_collateral else None
    requested = proposal.get("requested_amount_cr")
    poc_coverage = round(poc_net / requested, 2) if poc_net is not None and requested not in (None, 0) else None
    proposal_securities = []
    if proposal.get("primary_security"):
        proposal_securities.append({"label": "Primary Security", "value": proposal.get("primary_security"), "source": "Loan Application"})
    if proposal.get("collateral"):
        proposal_securities.append({"label": "Collateral", "value": proposal.get("collateral"), "source": "Loan Application"})
    collateral = {
        "gross_value_cr": _first(mock_collateral.get("gross_value_cr"), poc_gross),
        "net_value_cr": _first(mock_collateral.get("net_value_cr"), poc_net),
        "coverage_ratio": _first(mock_collateral.get("coverage_ratio"), poc_coverage),
        "securities": mock_collateral.get("securities") or proposal_securities or collateral_fields or [],
        "title_status": poc_collateral.get("title_status"),
        "valuation_status": poc_collateral.get("valuation_status"),
        "source": "synthetic_poc" if poc_collateral else ("document" if collateral_fields or proposal_securities else None),
        "synthetic": bool(poc_collateral),
    }
    mock_compliance, derived_compliance = mock.get("compliance") or {}, derived.get("compliance_engine_output") or {}
    compliance = {
        # Do not fabricate KYC/sanctions/PEP results. Missing private verification
        # stays pending in the UI.
        "kyc": _first(derived_compliance.get("kyc_status"), mock_compliance.get("kyc")),
        "sanctions": _first(screening.get("sanctions"), mock_compliance.get("sanctions")),
        "pep": _first(screening.get("pep"), mock_compliance.get("pep")),
        "adverse_media": _first(screening.get("adverse_media"), mock_compliance.get("adverse_media")),
        "policy_observations": derived_compliance.get("policy_observations") or mock_compliance.get("policy_observations") or [],
        "source": "api" if screening else ("mock" if mock_compliance else None),
    }
    sources = []
    if external_data.get("mock_matched"):
        sources.append({"type": "mock_api", "label": "Synthetic external API data", "status": "available"})
    if any(v is not None for v in metrics.values()):
        sources.append({"type": "documents", "label": "Uploaded financial documents", "status": "available"})
    if document_proposal:
        sources.append({"type": "proposal_document", "label": document_proposal.get("source_document") or "Uploaded loan application", "status": "available"})
    if mca:
        sources.append({"type": "mca", "label": "MCA / FileSure", "status": "available"})
    if public_information.get("mode") != "off":
        sources.append({"type": "public_search", "label": f"Public search ({public_information.get('mode')})", "status": "available"})
    return {
        "borrower": borrower, "proposal": proposal, "financials": financials, "ratios": ratio_context,
        "credit": credit, "risk": risk, "collateral": collateral, "compliance": compliance,
        "public_information": public_information, "data_sources": sources, "data_mode": external_data.get("mode"),
    }
