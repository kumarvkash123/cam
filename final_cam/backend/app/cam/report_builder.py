"""Build deterministic CAM report cards from data already present in the POC."""
from typing import Any, Dict, List

from app.cam.loan_summary import build_loan_summary
from docx.shared import Pt
from app.cam.borrower_information import build_borrower_information


def _value(v):
    return "Not available" if v in (None, "", []) else v


def _doc_rows(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "file": d.get("original_filename"),
            "type": d.get("display_name") or str(d.get("doc_type") or "Document").replace("_", " ").title(),
            "status": d.get("status", "processed"),
        }
        for d in documents
    ]


def _financial_report(summary: Dict[str, Any]) -> Dict[str, Any]:
    metrics = summary.get("financial_metrics_raw") or {}
    ratios = summary.get("ratios") or {}
    trend = summary.get("financial_trend") or {}
    years = summary.get("financial_years") or []

    def money(value):
        if value is None:
            return None
        try:
            return f"₹{float(value) / 10000000:.2f} Cr"
        except (TypeError, ValueError):
            return str(value)

    def ratio(value, suffix="x"):
        if value is None:
            return None
        try:
            return f"{float(value):.2f}{suffix}"
        except (TypeError, ValueError):
            return str(value)

    rows = []
    labels = [
        ("Total Revenue", metrics.get("total_revenue"), "money"),
        ("EBITDA", metrics.get("ebitda"), "money"),
        ("PAT", metrics.get("pat"), "money"),
        ("Net Worth", metrics.get("net_worth"), "money"),
        ("Total Debt", metrics.get("total_debt"), "money"),
        ("Working Capital", metrics.get("working_capital"), "money"),
        ("DSCR", ratios.get("dscr"), "x"),
        ("Debt / Equity", ratios.get("debt_equity"), "x"),
        ("Current Ratio", ratios.get("current_ratio"), "x"),
        ("Quick Ratio", ratios.get("quick_ratio"), "x"),
        ("Interest Coverage", ratios.get("interest_coverage"), "x"),
        ("Gross Margin", ratios.get("gross_margin"), "%"),
        ("EBITDA Margin", ratios.get("ebitda_margin"), "%"),
        ("PAT Margin", ratios.get("pat_margin"), "%"),
        ("ROCE", ratios.get("roce"), "%"),
    ]
    for label, val, unit in labels:
        if val is None:
            continue
        text = money(val) if unit == "money" else ratio(val, "%" if unit == "%" else "x")
        rows.append({"label": label, "value": text})

    trend_rows = []
    trend_data = []
    names = ["Revenue", "EBITDA", "PAT", "Net Worth", "Total Debt", "Working Capital"]
    for name in names:
        series = trend.get(name) or []
        if not series:
            continue
        used_years = years[-len(series):] if years else [f"Period {i + 1}" for i in range(len(series))]
        trend_rows.append({
            "label": name,
            "values": [money(x) for x in series],
            "years": used_years,
        })
        trend_data.append({
            "label": name,
            "years": used_years,
            "values": [float(x) if x is not None else None for x in series],
        })

    ratio_items = []
    ratio_defs = [
        ("DSCR", ratios.get("dscr"), "x"),
        ("Debt / Equity", ratios.get("debt_equity"), "x"),
        ("Current Ratio", ratios.get("current_ratio"), "x"),
        ("Interest Coverage", ratios.get("interest_coverage"), "x"),
        ("Gross Margin", ratios.get("gross_margin"), "%"),
        ("EBITDA Margin", ratios.get("ebitda_margin"), "%"),
        ("PAT Margin", ratios.get("pat_margin"), "%"),
        ("ROCE", ratios.get("roce"), "%"),
    ]
    for label, val, unit in ratio_defs:
        if val is not None:
            ratio_items.append({"label": label, "value": ratio(val, unit)})

    highlight_items = []
    for label, key in [
        ("Total Revenue", "total_revenue"),
        ("EBITDA", "ebitda"),
        ("PAT", "pat"),
        ("Net Worth", "net_worth"),
        ("Total Debt", "total_debt"),
        ("Working Capital", "working_capital"),
    ]:
        value = metrics.get(key)
        if value is not None:
            highlight_items.append({"label": label, "value": money(value)})

    insights = []
    revenue_growth = summary.get("revenue_growth")
    if revenue_growth is not None:
        direction = "grew" if revenue_growth >= 0 else "declined"
        insights.append(f"Revenue {direction} by {abs(float(revenue_growth)):.1f}% in the latest reported period.")
    if ratios.get("ebitda_margin") is not None:
        insights.append(f"Latest EBITDA margin is {float(ratios['ebitda_margin']):.2f}%.")
    if ratios.get("pat_margin") is not None:
        insights.append(f"Latest PAT margin is {float(ratios['pat_margin']):.2f}%.")
    if ratios.get("debt_equity") is not None:
        insights.append(f"Debt-to-equity is {float(ratios['debt_equity']):.2f}x based on extracted financials.")
    if ratios.get("dscr") is not None:
        insights.append(f"DSCR is {float(ratios['dscr']):.2f}x based on the available financial evidence.")
    if not insights:
        insights.append("Financial insights will appear when structured financial values are available from uploaded statements.")

    base_dscr = ratios.get("dscr")
    try:
        base_dscr = float(base_dscr) if base_dscr is not None else None
    except (TypeError, ValueError):
        base_dscr = None

    stress_testing = []
    scenarios = [
        ("Revenue -10%", "Revenue decrease by 10%", -12, 0.88, "Moderate"),
        ("EBITDA -10%", "EBITDA decrease by 10%", -15, 0.85, "Moderate"),
        ("Interest Rate +1%", "Interest rate increase by 1%", -8, 0.92, "Low"),
        ("Combined Stress", "Revenue -10% and interest rate +1%", -20, 0.80, "High"),
    ]
    for name, assumption, impact, factor, liquidity in scenarios:
        projected = round(base_dscr * factor, 2) if base_dscr is not None else None
        stress_testing.append({
            "scenario": name,
            "assumption": assumption,
            "impact": f"{impact}%",
            "dscr_projected": f"{projected:.2f}x" if projected is not None else "Not available",
            "liquidity_impact": liquidity,
        })

    def assessment(value, good, watch, good_text, watch_text, bad_text, reverse=False):
        if value is None:
            return "Not available"
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "Not available"
        if reverse:
            return good_text if value <= good else watch_text if value <= watch else bad_text
        return good_text if value >= good else watch_text if value >= watch else bad_text

    credit_evaluation = [
        {
            "label": "Overall Financial Health",
            "value": assessment(ratios.get("current_ratio"), 1.25, 1.0, "Good", "Moderate", "Weak"),
        },
        {
            "label": "Repayment Capacity",
            "value": assessment(ratios.get("dscr"), 1.5, 1.0, "Strong", "Moderate", "Weak"),
        },
        {
            "label": "Leverage Position",
            "value": assessment(ratios.get("debt_equity"), 1.5, 2.5, "Comfortable", "Moderate", "High", reverse=True),
        },
        {
            "label": "Risk Rating (Financial)",
            "value": assessment(ratios.get("dscr"), 1.5, 1.0, "Low", "Moderate", "High"),
        },
    ]

    return {
        "key": "financial_analysis",
        "title": "Financial Analysis",
        "available": bool(rows),
        "summary": "Financial indicators and ratios calculated deterministically from the uploaded financial statement.",
        "sections": [
            {"title": "Latest Financial Position", "rows": rows},
            {"title": "3-Year Trend", "trend": trend_rows},
        ],
        "data": {
            "years": years,
            "trends": trend_data,
            "ratios": ratio_items,
            "highlights": highlight_items,
            "insights": insights,
            "stress_testing": stress_testing,
            "credit_evaluation": credit_evaluation,
        },
    }

def build_business_overview(state: Dict[str, Any], summary: Dict[str, Any], borrower: Dict[str, Any]) -> Dict[str, Any]:
    enriched = state.get("business_overview_cache") or {}
    if enriched:
        model = enriched.get("business_model") or {}
        revenue = enriched.get("revenue_profile") or {}
        market = enriched.get("market_position") or {}
        footprint = enriched.get("operating_footprint") or {}
        rows = [
            {"label": "Business Type", "value": _value(model.get("type"))},
            {"label": "Industry", "value": _value(model.get("industry"))},
            {"label": "Customer Model", "value": _value(model.get("customer_model"))},
            {"label": "Latest Revenue (Cr)", "value": _value(revenue.get("latest_revenue_cr"))},
            {"label": "Latest Revenue Growth", "value": _value(revenue.get("latest_growth_pct"))},
            {"label": "Revenue CAGR", "value": _value(revenue.get("cagr_pct"))},
            {"label": "Registered Office", "value": _value(footprint.get("registered_office"))},
            {"label": "Credit Rating", "value": _value(market.get("credit_rating"))},
        ]
        return {
            "title": "Business Overview",
            "available": True,
            "summary": enriched.get("ai_overview") or "Business Overview prepared from normalized borrower, document, financial and external evidence.",
            "sections": [
                {"title": "Business Profile", "rows": rows},
                {"title": "Products / Services", "bullets": [x.get("name") for x in enriched.get("products_services", []) if x.get("name")] or ["Not available from current structured evidence."]},
                {"title": "Business Strengths", "bullets": enriched.get("strengths") or ["No specific strength calculated from current evidence."]},
                {"title": "Business Risks / Gaps", "bullets": enriched.get("business_risks") or ["No material business risk item available from current structured evidence."]},
            ],
        }
    b = borrower.get("borrower_details") or {}
    metrics = summary.get("financial_metrics_raw") or {}
    ratios = summary.get("ratios") or {}
    trend = summary.get("financial_trend") or {}
    rev = trend.get("Revenue") or []
    ebitda = trend.get("EBITDA") or []
    observations = []
    if len(rev) >= 2 and rev[-2] not in (None, 0):
        observations.append(f"Revenue grew {((rev[-1]-rev[-2])/rev[-2])*100:.2f}% in the latest reported year.")
    if metrics.get("ebitda") is not None and metrics.get("total_revenue") not in (None, 0):
        observations.append(f"Latest EBITDA margin is {ratios.get('ebitda_margin', 0):.2f}%.")
    if ratios.get("debt_equity") is not None:
        observations.append(f"Latest debt-to-equity is {ratios['debt_equity']:.2f}x.")
    rows = [
        {"label": "Company", "value": _value(b.get("company_name"))},
        {"label": "Industry", "value": _value(b.get("industry"))},
        {"label": "Constitution", "value": _value(b.get("constitution"))},
        {"label": "Incorporation Year", "value": _value(b.get("year_of_incorporation"))},
        {"label": "Registered Office", "value": _value(b.get("registered_office"))},
        {"label": "MCA Status", "value": _value(b.get("company_status"))},
        {"label": "Paid-up Capital", "value": _value(b.get("paid_up_capital"))},
        {"label": "Authorised Capital", "value": _value(b.get("authorised_capital"))},
    ]
    return {"title": "Business Overview", "available": bool(rows), "summary": "Business profile prepared only from the current borrower, MCA and financial data. Missing business facts are not invented.", "sections": [{"title": "Company Profile", "rows": rows}, {"title": "Financial Business Observations", "bullets": observations or ["No additional business observations can be calculated from the current data."]}]}


def _generic_report(title: str, summary: str, documents: List[Dict[str, Any]], keywords: List[str] = None) -> Dict[str, Any]:
    keywords = keywords or []
    matched = []
    for d in documents:
        dtype = str(d.get("doc_type") or "").lower()
        if not keywords or any(k in dtype for k in keywords):
            matched.append(d)
    rows = []
    for d in matched:
        fields = d.get("extracted_fields") or {}
        rows.append({"label": d.get("original_filename", "Document"), "value": f"{d.get('display_name') or d.get('doc_type')} — {len(fields)} structured field(s)"})
    return {"title": title, "available": bool(rows), "summary": summary, "sections": [{"title": "Available Data", "rows": rows or [{"label": "Status", "value": "No structured data available in the current POC."}]}]}


def build_cam_reports(state: Dict[str, Any], documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    summary = build_loan_summary(state, documents)
    borrower = build_borrower_information(state, documents)
    reports = []
    reports.append({"title": "Loan Summary", "available": True, "summary": summary.get("executive_summary", "Loan summary prepared from current data."), "sections": [{"title": "Loan Details", "rows":[{"label": k.replace("_", " ").title(), "value": _value(v)} for k,v in (summary.get("loan_details") or {}).items()]}, {"title":"Key Financial Indicators", "rows":[{"label":k,"value":_value(v)} for k,v in summary.get("financial_indicators",[])]}]})
    reports.append({"title": "Borrower Information", "available": True, "summary": borrower.get("verification_summary", {}).get("message", "Borrower information prepared."), "sections": [{"title":"Borrower Details", "rows":[{"label":k.replace("_"," ").title(),"value":_value(v)} for k,v in (borrower.get("borrower_details") or {}).items()]}, {"title":"Verification Summary", "rows":[{"label":"Total Sources Checked","value":borrower.get("verification_summary",{}).get("total_sources",0)},{"label":"Verified","value":borrower.get("verification_summary",{}).get("verified",0)},{"label":"Validated","value":borrower.get("verification_summary",{}).get("validated",0)},{"label":"Pending / Issues","value":borrower.get("verification_summary",{}).get("pending_issues",0)}]}]})
    reports.append(build_business_overview(state, summary, borrower))
    reports.append(_financial_report(summary))
    reports.append(_generic_report("Credit History", "Credit-history report uses only credit/bank/ITR data currently present in uploaded documents.", documents, ["cibil", "credit", "bank_statement", "itr"]))
    reports.append(_generic_report("Risk Assessment & Mitigation", "Preliminary risk report based on available financial and borrower data. No unavailable risk facts are fabricated.", documents))
    reports.append(_generic_report("Collateral Details", "Collateral information is shown only when collateral/security documents are present.", documents, ["collateral", "security", "property"]))
    reports.append({"title":"Loan Terms & Conditions", "available": bool(state.get("loan_type") or state.get("loan_amount")), "summary":"Current POC loan terms are limited to the conversational loan type and requested amount.", "sections":[{"title":"Captured Terms", "rows":[{"label":"Facility Type","value":_value(state.get("loan_type"))},{"label":"Requested Amount","value":_value(state.get("loan_amount"))},{"label":"Purpose","value":"Not available in current POC"},{"label":"Tenure","value":"Not available in current POC"},{"label":"Interest Rate","value":"Not available in current POC"},{"label":"Repayment","value":"Not available in current POC"}]}]})
    reports.append(_generic_report("Regulatory Compliance", "Compliance report reflects only regulatory documents and MCA status currently available.", documents, ["gst", "itr", "pan", "udyam", "certificate"]))
    
    industry_peer = state.get("industry_peer_cache") or {}
    if industry_peer:
        overview = industry_peer.get("industry_overview") or {}
        peer_rows = []
        for r in industry_peer.get("peer_comparison") or []:
            peer_rows.append({"label": r.get("metric"), "value": f"Borrower {r.get('borrower')} | {r.get('benchmark_label')}: {r.get('benchmark')} | {r.get('position')}"})
        reports.append({
            "title": "Peer Benchmarking & Market / Industry Analysis",
            "available": True,
            "summary": (industry_peer.get("commentary") or {}).get("text") or "Industry and peer context prepared from configured evidence.",
            "sections": [
                {"title": "Industry Overview", "rows": [
                    {"label": "Industry", "value": _value(overview.get("industry"))},
                    {"label": "Industry Growth", "value": _value(overview.get("growth_pct"))},
                    {"label": "Outlook", "value": _value(overview.get("outlook"))},
                    {"label": "Industry Median EBITDA Margin", "value": _value(overview.get("industry_median_ebitda_margin_pct"))},
                ]},
                {"title": "Peer Comparison", "rows": peer_rows or [{"label": "Status", "value": "No source-backed peer benchmark is available."}]},
                {"title": "Relative Strengths", "bullets": industry_peer.get("strengths") or ["No source-backed relative strength available."]},
                {"title": "Industry / Peer Risks", "bullets": industry_peer.get("risks") or ["No source-backed industry/peer risk observation available."]},
            ],
        })
    else:
        reports.append(_generic_report("Peer Benchmarking & Market / Industry Analysis", "Point 10 has not yet been prepared; unavailable peer metrics are not estimated.", documents))
    return reports
