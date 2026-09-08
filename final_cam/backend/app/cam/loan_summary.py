"""Deterministic Loan Summary builder for the CAM POC.

Executive summary text is produced by a bounded, single-call LLM narrative
(generate_loan_summary_narrative) that is only ever handed already-computed,
already-verified facts (loan details, financial ratios, rule-evaluated risk
flags, collateral field extracts). The LLM never sees raw documents and is
never the source of a number or a risk determination -- it only writes about
facts this module already established. If the LLM call fails, the caller receives explicit LLM status/error information; no narrative fallback is presented as an AI summary.
"""
import re
import logging
from typing import Any, Dict, List, Optional

from app.cam.requirement_matrix import compute_progress
from app.cam.loan_summary_service import build_loan_summary_context, collect_external_data, collect_public_information
from app.config import get_groq_api_key, get_groq_model

LOGGER = logging.getLogger(__name__)

_LLM_IMPORT_ERROR = None
try:
    from app.cam.llm_service import generate_loan_summary_narrative
    from app.cam.llm_gateway import LLMGatewayError
except Exception as exc:  # pragma: no cover
    # Keep the Loan Summary screen available even if the optional LLM stack
    # cannot import, but do not hide the root cause. It is surfaced in the API
    # response and backend logs for debugging.
    generate_loan_summary_narrative = None
    LLMGatewayError = RuntimeError
    _LLM_IMPORT_ERROR = repr(exc)
    LOGGER.exception("Loan Summary LLM stack failed to import")


def _clean_text(value: Any) -> str:
    return str(value or "").replace("\xa0", " ").strip()


def _number(value: str) -> Optional[float]:
    if not value:
        return None
    s = _clean_text(value).replace("₹", "").replace("Rs.", "").replace("Rs", "")
    s = s.replace("(", "-").replace(")", "")
    s = re.sub(r"[^0-9.\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def _format_inr(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    sign = "-" if value < 0 else ""
    n = abs(value)
    if n >= 10_000_000:
        return f"{sign}₹ {n / 10_000_000:.2f} Cr"
    if n >= 100_000:
        return f"{sign}₹ {n / 100_000:.2f} Lakh"
    return f"{sign}₹ {n:,.0f}"


def _numeric_tokens(lines: List[str]) -> List[float]:
    values = []
    for line in lines:
        for raw in re.findall(r"(?:₹|Rs\.?\s*)?[-(]?\d[\d,]*(?:\.\d+)?\)?", line):
            n = _number(raw)
            if n is not None and not (1900 <= abs(n) <= 2100):
                values.append(n)
    return values


def _find_series(text: str, labels: List[str], max_lines: int = 7) -> List[float]:
    lines = [x.strip() for x in (text or "").splitlines() if x.strip()]
    for label in labels:
        pattern = re.compile(r"(?<!\w)" + re.escape(label) + r"(?!\w)", re.I)
        for i, line in enumerate(lines):
            if pattern.search(line):
                values = _numeric_tokens(lines[i:i + max_lines])
                if len(values) >= 3:
                    return values[:3]
                if values:
                    return values[:1]
    return []


def _find_latest(text: str, labels: List[str]) -> Optional[float]:
    series = _find_series(text, labels)
    return series[-1] if series else None


def _find_years(text: str) -> List[str]:
    years = []
    for m in re.finditer(r"(?:FY\s*)?(20\d{2})\s*[-–/]\s*(\d{2,4})", text or "", re.I):
        y, end = m.group(1), m.group(2)
        label = f"{y}-{end if len(end) == 2 else end[-2:]}"
        if label not in years:
            years.append(label)
    return years[-5:]


def _mca_company_data(mca: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not mca:
        return {}
    data = mca.get("data") if isinstance(mca, dict) else mca
    data = data or {}
    master = data.get("masterData") or {}
    company = master.get("companyData") or {}
    addresses = company.get("MCAMDSCompanyAddress") or []
    return {
        "cin": data.get("cin") or company.get("cin"),
        "company_name": data.get("company") or company.get("companyName"),
        "pan": company.get("pan"),
        "gstin": company.get("gstin"),
        "roc": company.get("rocCode"),
        "company_type": company.get("companyType") or company.get("classOfCompany"),
        "listed": company.get("whetherListedOrNot"),
        "status": company.get("companyStatus"),
        "incorporation_date": company.get("dateOfIncorporation"),
        "address": addresses[0] if addresses else {},
    }


def _extract_financial_metrics(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    text = "\n".join(_clean_text(d.get("extracted_text")) for d in documents if d.get("extracted_text"))
    multiplier = 10_000_000 if re.search(r"(?:₹\s*)?(?:in\s+)?(?:crores?|cr)\b", text, re.I) else 100_000 if re.search(r"(?:₹\s*)?(?:in\s+)?(?:lakhs?|lacs?)\b", text, re.I) else 1.0

    label_map = {
        "total_revenue": ["Revenue from Operations", "Total Revenue", "Turnover", "Sales"],
        "ebitda": ["EBITDA", "Operating EBITDA"],
        "ebit": ["EBIT"],
        "pat": ["Profit After Tax (PAT)", "Profit After Tax", "PAT", "Net Profit", "Profit for the year"],
        "net_worth": ["Shareholders' Equity / Net Worth", "Net Worth", "Networth", "Shareholders' Funds", "Total Equity"],
        "total_debt": ["Total Debt", "Total Borrowings", "Total Borrowing"],
        "fixed_assets": ["Fixed Assets"],
        "inventory": ["Inventory"],
        "trade_payables": ["Trade Payables"],
        "short_term_borrowings": ["Short-term Borrowings", "Short Term Borrowings"],
        "other_current_liabilities": ["Other Current Liabilities"],
        "total_assets": ["Total Assets"],
        "total_liabilities": ["Total Liabilities"],
        "interest": ["Finance Cost / Interest", "Finance Cost", "Interest Expense", "Interest"],
        "cfo": ["Cash Flow from Operations"],
        "capex": ["Capital Expenditure", "Capex"],
        "fcf": ["Free Cash Flow"],
        "dscr": ["DSCR", "Debt Service Coverage Ratio"],
    }
    metrics = {key: _find_latest(text, labels) for key, labels in label_map.items()}
    if multiplier != 1.0:
        # DSCR is a ratio, never a currency amount -- don't rescale it.
        metrics = {
            key: (value * multiplier if value is not None and key != "dscr" else value)
            for key, value in metrics.items()
        }

    if metrics.get("total_assets") is not None and metrics.get("fixed_assets") is not None:
        metrics["current_assets"] = metrics["total_assets"] - metrics["fixed_assets"]
    else:
        metrics["current_assets"] = _find_latest(text, ["Current Assets", "Total Current Assets"])
        if metrics["current_assets"] is not None:
            metrics["current_assets"] *= multiplier

    current_components = [metrics.get("trade_payables"), metrics.get("short_term_borrowings"), metrics.get("other_current_liabilities")]
    if all(v is not None for v in current_components):
        metrics["current_liabilities"] = sum(current_components)
    else:
        metrics["current_liabilities"] = _find_latest(text, ["Current Liabilities", "Total Current Liabilities"])
        if metrics["current_liabilities"] is not None:
            metrics["current_liabilities"] *= multiplier

    ratios: Dict[str, float] = {}
    if metrics.get("total_debt") is not None and metrics.get("net_worth") not in (None, 0):
        ratios["debt_equity"] = metrics["total_debt"] / metrics["net_worth"]
    if metrics.get("current_assets") is not None and metrics.get("current_liabilities") not in (None, 0):
        ratios["current_ratio_calculated"] = metrics["current_assets"] / metrics["current_liabilities"]
    if metrics.get("total_revenue") not in (None, 0):
        if metrics.get("ebitda") is not None:
            ratios["ebitda_margin_calculated"] = metrics["ebitda"] / metrics["total_revenue"] * 100
        if metrics.get("pat") is not None:
            ratios["pat_margin_calculated"] = metrics["pat"] / metrics["total_revenue"] * 100
    if metrics.get("ebit") is not None and metrics.get("interest") not in (None, 0):
        ratios["interest_coverage_calculated"] = metrics["ebit"] / metrics["interest"]
    if metrics.get("dscr") is not None:
        ratios["dscr"] = metrics["dscr"]

    # If the financial statement explicitly reports ratios, use the latest
    # reported value for the display and retain calculated values above.
    for key, labels in {
        "current_ratio": ["Current Ratio"],
        "quick_ratio": ["Quick Ratio"],
        "ebitda_margin": ["EBITDA Margin"],
        "pat_margin": ["PAT Margin"],
        "interest_coverage": ["Interest Coverage Ratio", "Interest Coverage"],
        "roce": ["ROCE"],
    }.items():
        series = _find_series(text, labels)
        if series:
            ratios[key] = series[-1]

    trends = {}
    for name, labels in {
        "Revenue": label_map["total_revenue"], "EBITDA": label_map["ebitda"],
        "PAT": label_map["pat"], "Net Worth": label_map["net_worth"],
        "Total Debt": label_map["total_debt"], "CFO": label_map["cfo"],
        "Free Cash Flow": label_map["fcf"],
    }.items():
        series = _find_series(text, labels)
        if series:
            trends[name] = [x * multiplier for x in series]

    revenue_growth = []
    revenue = trends.get("Revenue", [])
    for previous, current in zip(revenue, revenue[1:]):
        if previous not in (None, 0):
            revenue_growth.append((current - previous) / previous * 100)

    return {"metrics": metrics, "ratios": ratios, "years": _find_years(text), "trends": trends, "revenue_growth": revenue_growth}


COLLATERAL_FIELD_KEYWORDS = ["property", "security", "collateral", "valuation", "mortgage", "charge", "guarantee"]


def _extract_collateral_fields(documents: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Best-effort collateral extract from already-classified document fields.

    This is intentionally thin (keyword match on extracted field names) --
    it mirrors the existing filter in core.py's report builder. A proper
    structured collateral module (type / valuation / coverage ratio) is a
    separate piece of work; until then this at least gives the narrative
    something real to reference instead of nothing.
    """
    items: List[Dict[str, str]] = []
    for d in documents or []:
        fields = d.get("extracted_fields") or {}
        for key, value in fields.items():
            if any(word in key.lower() for word in COLLATERAL_FIELD_KEYWORDS):
                cleaned = _clean_text(value)
                if cleaned:
                    items.append({"field": key, "value": cleaned})
    return items[:20]


# ---------------------------------------------------------------------------
# Risk rules: deterministic, auditable, configurable -- exactly like
# REQUIREMENT_MATRIX in requirement_matrix.py. The LLM narrative is only ever
# shown the OUTPUT of this table; it never evaluates a threshold itself.
# ---------------------------------------------------------------------------
RISK_RULES = [
    {"key": "debt_equity", "source": "ratios", "op": "gt", "threshold": 3.0,
     "label": "Debt/Equity ratio is {value:.2f}x, above the policy threshold of {threshold:.1f}x"},
    {"key": "current_ratio", "source": "ratios", "op": "lt", "threshold": 1.0,
     "label": "Current ratio is {value:.2f}x, below the policy minimum of {threshold:.1f}x"},
    {"key": "interest_coverage", "source": "ratios", "op": "lt", "threshold": 1.5,
     "label": "Interest coverage ratio is {value:.2f}x, below the policy minimum of {threshold:.1f}x"},
    {"key": "dscr", "source": "ratios", "op": "lt", "threshold": 1.2,
     "label": "DSCR is {value:.2f}x, below the policy minimum of {threshold:.1f}x"},
    {"key": "pat_margin", "source": "ratios", "op": "lt", "threshold": 0.0,
     "label": "PAT margin is negative ({value:.2f}%)"},
    {"key": "pat", "source": "metrics", "op": "lt", "threshold": 0.0,
     "label": "Reported PAT is negative"},
]

_OPS = {"gt": lambda a, b: a > b, "lt": lambda a, b: a < b}


def evaluate_risk_rules(metrics: Dict[str, Any], ratios: Dict[str, Any], mca: Dict[str, Any]) -> List[str]:
    flags: List[str] = []
    for rule in RISK_RULES:
        source = metrics if rule["source"] == "metrics" else ratios
        value = source.get(rule["key"])
        if value is None:
            continue
        if _OPS[rule["op"]](value, rule["threshold"]):
            flags.append(rule["label"].format(value=value, threshold=rule["threshold"]))
    if mca.get("status") and str(mca["status"]).lower() != "active":
        flags.append(f"MCA company status is '{mca['status']}', requires review")
    if not mca:
        flags.append("MCA enrichment not available")
    return flags


def bucket_readiness(checks: List[bool], mca_fetch_status: Optional[str], progress: Dict[str, Any]) -> Dict[str, Any]:
    """Completed / In Progress / Pending counts for the CAM Readiness donut.

    completed  -- boolean checks that are satisfied, plus mandatory documents
                  already uploaded.
    in_progress -- an MCA fetch was attempted but hasn't resolved successfully
                  yet (failed once, may be retried).
    pending    -- mandatory documents from the requirement matrix that are
                  still missing.
    """
    completed = sum(1 for c in checks if c) + progress.get("uploaded_mandatory", 0)
    in_progress = 1 if mca_fetch_status == "failed" else 0
    pending = len(progress.get("missing_mandatory", []))
    total = completed + in_progress + pending
    score = round(completed / total * 100) if total else 0
    return {"completed": completed, "in_progress": in_progress, "pending": pending, "total": total, "score": score}


def _template_executive_summary(company_name, amount_display, loan_type, metrics, mca) -> str:
    executive = (
        f"{company_name} has requested {amount_display} under the {loan_type or 'proposed'} facility. "
        f"Based on the uploaded financial statement, reported revenue is {_format_inr(metrics.get('total_revenue')) or 'not available'} "
        f"and PAT is {_format_inr(metrics.get('pat')) or 'not available'}."
    )
    if mca.get("status"):
        executive += f" MCA records show the company as {mca['status']}."
    return executive


def _cr_display(value: Any) -> str:
    try:
        return f"₹ {float(value):,.2f} Cr"
    except (TypeError, ValueError):
        return "Not available"


def _ratio_display(value: Any, suffix: str = "x") -> str:
    try:
        return f"{float(value):.2f}{suffix}"
    except (TypeError, ValueError):
        return "Not available"


def build_loan_summary(state: Dict[str, Any], documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build the dedicated Step-5 Loan Summary payload.

    Existing document/MCA extraction remains authoritative. For the POC we can
    enrich missing fields from the packaged five-company mock APIs. Public data
    can come from the mock feed or Google search depending on environment flags.
    Only this small structured context is handed to Groq.
    """
    financial = _extract_financial_metrics(documents)
    mca = _mca_company_data((state.get("mca") or {}).get("data"))
    mca_fetch_status = (state.get("mca") or {}).get("status")
    metrics, ratios = financial["metrics"], financial["ratios"]
    risk_flags = evaluate_risk_rules(metrics, ratios, mca)
    collateral_fields = _extract_collateral_fields(documents)

    external_data = collect_external_data(state)
    mock_ctx = (external_data.get("derived") or {}).get("loan_summary_context") or {}
    mock_industry = (mock_ctx.get("borrower") or {}).get("industry") or ""
    public_information = collect_public_information(state, external_data, mock_industry)

    context = build_loan_summary_context(
        state=state,
        metrics=metrics,
        ratios=ratios,
        mca=mca,
        risk_flags=risk_flags,
        collateral_fields=collateral_fields,
        external_data=external_data,
        public_information=public_information,
    )

    borrower = context["borrower"]
    proposal = context["proposal"]
    financials = context["financials"]
    clean_ratios = context["ratios"]
    credit = context["credit"]
    risk = context["risk"]
    collateral = context["collateral"]
    compliance = context["compliance"]

    uploaded_doc_types = [d.get("doc_type") for d in documents if d.get("doc_type")]
    progress = compute_progress(proposal.get("facility_type") or state.get("loan_type") or "msme", uploaded_doc_types)
    checks = [
        bool(borrower.get("name")), bool(proposal.get("facility_type")), proposal.get("requested_amount_cr") is not None,
        bool(proposal.get("purpose")), bool(proposal.get("tenure_months")), bool(documents),
        financials.get("revenue_cr") is not None, financials.get("pat_cr") is not None,
        credit.get("bureau_score") is not None, collateral.get("coverage_ratio") is not None,
    ]
    readiness = bucket_readiness(checks, mca_fetch_status, progress)
    readiness["missing_items"] = [
        str(item).replace("_", " ").title()
        for item in (progress.get("missing_mandatory") or [])
    ]
    if mca_fetch_status == "failed":
        readiness.setdefault("in_progress_items", []).append("MCA enrichment retry required")

    financial_rows = [
        ("Revenue", _cr_display(financials.get("revenue_cr"))),
        ("EBITDA", _cr_display(financials.get("ebitda_cr"))),
        ("PAT", _cr_display(financials.get("pat_cr"))),
        ("Net Worth", _cr_display(financials.get("net_worth_cr"))),
        ("Total Debt", _cr_display(financials.get("total_debt_cr"))),
        ("Working Capital", _cr_display(financials.get("working_capital_cr"))),
        ("DSCR", _ratio_display(clean_ratios.get("dscr"))),
        ("ICR", _ratio_display(clean_ratios.get("icr"))),
        ("Debt / Equity", _ratio_display(clean_ratios.get("debt_equity"))),
        ("Current Ratio", _ratio_display(clean_ratios.get("current_ratio"))),
        ("EBITDA Margin", _ratio_display(clean_ratios.get("ebitda_margin_pct"), "%")),
        ("PAT Margin", _ratio_display(clean_ratios.get("pat_margin_pct"), "%")),
    ]

    company = {
        "name": borrower.get("name"), "cin": borrower.get("cin"), "pan": borrower.get("pan"),
        "gstin": borrower.get("gstin"), "status": borrower.get("mca_status"),
        "industry": borrower.get("industry"), "location": borrower.get("location"),
        "existing_customer": borrower.get("existing_customer"),
    }
    loan_details = {
        "requested_amount": _cr_display(proposal.get("requested_amount_cr")),
        "requested_amount_cr": proposal.get("requested_amount_cr"),
        "facility_type": proposal.get("facility_type") or "Not available",
        "purpose": proposal.get("purpose") or "Not available",
        "tenure": f"{proposal.get('tenure_months')} months" if proposal.get("tenure_months") not in (None, "") else "Not available",
        "interest_rate": f"{proposal.get('interest_rate_pct')}%" if proposal.get("interest_rate_pct") not in (None, "") else "Not available",
        "repayment": proposal.get("repayment") or "Not available",
        "rm": proposal.get("rm") or "Not available",
    }

    # IMPORTANT: Step 5 must show a real Groq-generated narrative or an explicit
    # Groq error. Do not silently substitute a deterministic narrative because
    # that makes it look as if the LLM call succeeded when it did not.
    executive_summary = None
    summary_source = "groq_not_attempted"
    llm_status = {
        "configured": bool(get_groq_api_key()),
        "model": get_groq_model(),
        "status": "not_attempted",
        "error": None,
        "status_code": None,
    }

    if generate_loan_summary_narrative is None:
        llm_status["status"] = "import_error"
        llm_status["error"] = _LLM_IMPORT_ERROR or "Loan Summary LLM service is unavailable."
        summary_source = "groq_failed"
    elif not get_groq_api_key():
        llm_status["status"] = "not_configured"
        llm_status["error"] = "GROQ_API_KEY is not configured in backend/.env."
        summary_source = "groq_failed"
    else:
        try:
            LOGGER.info(
                "Loan Summary Groq generation started model=%s company=%s",
                get_groq_model(),
                borrower.get("name"),
            )
            ai_summary = generate_loan_summary_narrative(context)
            if ai_summary and ai_summary.strip():
                executive_summary, summary_source = ai_summary.strip(), "ai_generated"
                llm_status["status"] = "success"
                LOGGER.info("Loan Summary Groq generation completed successfully")
            else:
                llm_status["status"] = "empty_response"
                llm_status["error"] = "Groq returned an empty Loan Summary response."
                summary_source = "groq_failed"
                LOGGER.warning("Loan Summary Groq returned an empty response")
        except LLMGatewayError as exc:
            llm_status["status"] = "provider_error"
            llm_status["error"] = str(exc)
            llm_status["status_code"] = getattr(exc, "status_code", None)
            summary_source = "groq_failed"
            LOGGER.exception("Loan Summary Groq provider error: %s", exc)
        except Exception as exc:
            llm_status["status"] = "unexpected_error"
            llm_status["error"] = f"{type(exc).__name__}: {exc}"
            summary_source = "groq_failed"
            LOGGER.exception("Unexpected Loan Summary Groq error")

    return {
        "generated_at": state.get("created_at"),
        "company": company,
        "loan_details": loan_details,
        "financial_indicators": financial_rows,
        "financial_metrics_raw": metrics,
        "ratios": clean_ratios,
        "financial_years": financial["years"],
        "financial_trend": financial["trends"],
        "revenue_growth": financial["revenue_growth"],
        "readiness": readiness,
        "executive_summary": executive_summary,
        "summary_source": summary_source,
        "llm_status": llm_status,
        "credit": credit,
        "risk": risk,
        "risk_flags": risk.get("major_risks") or [],
        "collateral": collateral,
        "collateral_fields": collateral.get("securities") or [],
        "compliance": compliance,
        "public_information": public_information,
        "data_sources": context.get("data_sources") or [],
        "data_mode": context.get("data_mode"),
        "context": context,
        "activities": [
            {"label": "Financial documents processed", "status": "completed" if documents else "pending"},
            {"label": "External company enrichment", "status": "completed" if external_data.get("mock_matched") or mca else "pending"},
            {"label": "Credit / bureau data", "status": "completed" if credit.get("bureau_score") is not None else "pending"},
            {"label": "Public information enrichment", "status": "completed" if public_information.get("mode") != "off" else "pending"},
        ],
    }

