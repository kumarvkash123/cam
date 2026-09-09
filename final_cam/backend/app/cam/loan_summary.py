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
import os
import json
from typing import Any, Dict, List, Optional

from app.cam.requirement_matrix import compute_progress
from app.cam.loan_summary_service import build_loan_summary_context, collect_external_data, collect_public_information
from app.cam.loan_summary_service.presentation_builder import build_presentation
from app.cam.extraction_ext import extract_annual_report_fields
from app.config import get_groq_api_key, get_groq_model

LOGGER = logging.getLogger(__name__)

FIN_DEBUG = str(os.getenv("CAM_FINANCIAL_DEBUG", "1")).strip().lower() not in {"0", "false", "off", "no"}
LS_DEBUG = str(os.getenv("CAM_LOAN_SUMMARY_DEBUG", "1")).strip().lower() not in {"0", "false", "off", "no"}

def _fin_debug(stage: str, payload: Any) -> None:
    """Emit a compact, searchable financial-pipeline trace.

    Set CAM_FINANCIAL_DEBUG=0 to disable.  Prefix is intentionally stable so
    PowerShell users can filter logs with: Select-String "CAM-FIN-DEBUG".
    """
    if not FIN_DEBUG:
        return
    try:
        rendered = json.dumps(payload, ensure_ascii=False, default=str, indent=2)
    except Exception:
        rendered = repr(payload)
    print(f"\n[CAM-FIN-DEBUG] {stage}\n{rendered}\n", flush=True)


def _ls_debug(stage: str, payload: Any) -> None:
    """Full Step-5 trace. Disable with CAM_LOAN_SUMMARY_DEBUG=0."""
    if not LS_DEBUG:
        return
    try:
        rendered = json.dumps(payload, ensure_ascii=False, default=str, indent=2)
    except Exception:
        rendered = repr(payload)
    print(f"\n[CAM-LS-DEBUG] {stage}\n{rendered}\n", flush=True)


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


def _financial_year_sort_key(value: Any):
    text = str(value or "")
    m = re.search(r"(20\d{2})\s*[-–/]\s*(\d{2,4})", text)
    if not m:
        return (0, 0)
    start = int(m.group(1))
    end = int(m.group(2))
    if end < 100:
        end = (start // 100) * 100 + end
    return (end, start)


def _annual_report_candidates(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    candidates = []
    for d in documents:
        stored_fields = d.get("extracted_fields") or {}
        if d.get("doc_type") != "annual_report" and stored_fields.get("document_kind") != "annual_report":
            continue

        # Re-parse the stored annual-report text with the current extractor at
        # Loan Summary time.  This makes the financial fix effective for CAMs
        # whose documents were uploaded before this code version (their DB row
        # may still contain old note-number values such as 28, 7, 8, 9).
        fields = stored_fields
        if d.get("extracted_text"):
            reparsed = extract_annual_report_fields(d.get("extracted_text") or "")
            if any(k.endswith("_current") for k in reparsed):
                fields = reparsed

        if any(k.endswith("_current") for k in fields):
            candidate = dict(d)
            candidate["extracted_fields"] = fields
            candidates.append(candidate)
            _fin_debug("annual_report_candidate", {
                "document": d.get("original_filename"),
                "doc_type": d.get("doc_type"),
                "financial_year": fields.get("financial_year"),
                "financial_unit": fields.get("financial_unit"),
                "revenue_from_operations_current": fields.get("revenue_from_operations_current"),
                "total_income_current": fields.get("total_income_current"),
                "profit_after_tax_current": fields.get("profit_after_tax_current"),
                "total_equity_current": fields.get("total_equity_current"),
                "total_current_assets_current": fields.get("total_current_assets_current"),
                "total_current_liabilities_current": fields.get("total_current_liabilities_current"),
            })
    return sorted(
        candidates,
        key=lambda d: _financial_year_sort_key((d.get("extracted_fields") or {}).get("financial_year")),
        reverse=True,
    )


def _unit_multiplier(unit: Any) -> Optional[float]:
    unit = str(unit or "").upper().strip()
    if unit == "INR_LAKH":
        return 100_000.0
    if unit == "INR_CRORE":
        return 10_000_000.0
    if unit == "INR_RUPEE":
        return 1.0
    return None


def _field_number(fields: Dict[str, Any], key: str) -> Optional[float]:
    value = fields.get(key)
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").replace("₹", "").strip())
    except (TypeError, ValueError):
        return None


def _currency_value(fields: Dict[str, Any], key: str, multiplier: float) -> Optional[float]:
    value = _field_number(fields, key)
    return value * multiplier if value is not None else None


def _validate_structured_financials(metrics: Dict[str, Any], ratios: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    revenue = metrics.get("total_revenue")
    pat = metrics.get("pat")
    equity = metrics.get("net_worth")
    ca = metrics.get("current_assets")
    cl = metrics.get("current_liabilities")
    if revenue is None or revenue <= 0:
        errors.append("total_revenue_missing_or_nonpositive")
    if pat is not None and revenue not in (None, 0) and abs(pat) > abs(revenue):
        errors.append("pat_exceeds_revenue")
    if equity is not None and equity <= 0:
        errors.append("net_worth_nonpositive")
    if ca is not None and ca < 0:
        errors.append("current_assets_negative")
    if cl is not None and cl < 0:
        errors.append("current_liabilities_negative")
    pm = ratios.get("pat_margin")
    if pm is not None and not (-100.0 <= pm <= 100.0):
        errors.append("pat_margin_out_of_range")
    cr = ratios.get("current_ratio")
    if cr is not None and not (0 <= cr <= 20):
        errors.append("current_ratio_out_of_range")
    de = ratios.get("debt_equity")
    if de is not None and not (0 <= de <= 50):
        errors.append("debt_equity_out_of_range")
    return errors

def _structured_financial_metrics(documents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Build Loan Summary metrics from the latest structured annual report.

    All returned currency metrics are normalized to INR RUPEES.  This keeps the
    existing context builder/display contract stable while eliminating the old
    whole-document unit guessing that could turn note numbers or share capital
    into revenue/PAT.
    """
    annual_reports = _annual_report_candidates(documents)
    if not annual_reports:
        return None

    latest = annual_reports[0]
    fields = latest.get("extracted_fields") or {}
    _fin_debug("selected_annual_report", {
        "document": latest.get("original_filename"),
        "financial_year": fields.get("financial_year"),
        "financial_unit": fields.get("financial_unit"),
        "raw_fields": {k: v for k, v in fields.items() if k.endswith("_current") or k in {"financial_year", "financial_unit"}},
        "critical_rows": {
            "revenue_from_operations": fields.get("revenue_from_operations_current"),
            "finance_cost": fields.get("finance_cost_current"),
            "depreciation": fields.get("depreciation_amortisation_current"),
            "inventory": fields.get("inventories_current"),
            "current_borrowings": fields.get("current_borrowings_current"),
            "non_current_borrowings": fields.get("non_current_borrowings_current"),
        },
    })
    multiplier = _unit_multiplier(fields.get("financial_unit"))
    if multiplier is None:
        # Do not silently guess units for audited financial statements.  If unit
        # metadata is unavailable, fall back to the legacy path rather than
        # producing a confidently wrong crore conversion.
        return None

    revenue_ops = _currency_value(fields, "revenue_from_operations_current", multiplier)
    total_income = _currency_value(fields, "total_income_current", multiplier)
    pbt = _currency_value(fields, "profit_before_tax_current", multiplier)
    pat = _currency_value(fields, "profit_after_tax_current", multiplier)
    finance = _currency_value(fields, "finance_cost_current", multiplier)
    depreciation = _currency_value(fields, "depreciation_amortisation_current", multiplier)
    equity = _currency_value(fields, "total_equity_current", multiplier)
    current_borrowings = _currency_value(fields, "current_borrowings_current", multiplier)
    non_current_borrowings = _currency_value(fields, "non_current_borrowings_current", multiplier)
    current_assets = _currency_value(fields, "total_current_assets_current", multiplier)
    current_liabilities = _currency_value(fields, "total_current_liabilities_current", multiplier)
    inventory = _currency_value(fields, "inventories_current", multiplier)

    debt_parts = [x for x in (current_borrowings, non_current_borrowings) if x is not None]
    total_debt = sum(debt_parts) if debt_parts else None

    # EBITDA is a deterministic reconstruction from audited PBT + finance cost
    # + depreciation/amortisation.  No LLM or synthetic ratio is involved.
    ebitda = (pbt + finance + depreciation) if None not in (pbt, finance, depreciation) else None
    ebit = (pbt + finance) if None not in (pbt, finance) else None

    metrics: Dict[str, Any] = {
        "latest_fy": fields.get("financial_year"),
        "total_revenue": total_income if total_income is not None else revenue_ops,
        "revenue_from_operations": revenue_ops,
        "other_income": _currency_value(fields, "other_income_current", multiplier),
        "ebitda": ebitda,
        "ebit": ebit,
        "pat": pat,
        "pbt": pbt,
        "net_worth": equity,
        "total_debt": total_debt,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        "inventory": inventory,
        "trade_payables": _currency_value(fields, "trade_payables_current", multiplier),
        "interest": finance,
        "depreciation": depreciation,
        "cfo": _currency_value(fields, "net_cash_from_operating_activities_current", multiplier),
    }

    ratios: Dict[str, float] = {}
    if total_debt is not None and equity not in (None, 0):
        ratios["debt_equity"] = total_debt / equity
    if current_assets is not None and current_liabilities not in (None, 0):
        ratios["current_ratio"] = current_assets / current_liabilities
        if inventory is not None:
            ratios["quick_ratio"] = (current_assets - inventory) / current_liabilities
    if metrics["total_revenue"] not in (None, 0):
        if ebitda is not None:
            ratios["ebitda_margin"] = ebitda / metrics["total_revenue"] * 100
        if pat is not None:
            ratios["pat_margin"] = pat / metrics["total_revenue"] * 100
    if ebitda is not None and finance not in (None, 0):
        # Preserve the CAM's existing EBITDA/finance-cost coverage convention.
        ratios["interest_coverage"] = ebitda / finance

    validation_errors = _validate_structured_financials(metrics, ratios)
    _fin_debug("normalized_structured_metrics", {
        "source_document": latest.get("original_filename"),
        "multiplier": multiplier,
        "metrics_rupees": metrics,
        "metrics_crore_preview": {k: (round(v / 10_000_000, 4) if isinstance(v, (int, float)) and k not in {"latest_fy"} else v) for k, v in metrics.items()},
        "ratios": ratios,
        "validation_errors": validation_errors,
    })
    if validation_errors:
        # Important: do not silently fall back to global regex when an annual
        # report was found but its structured values failed sanity checks.
        # Returning a safe empty financial set makes the UI show Not available
        # instead of impossible values such as 191,000% PAT margin.
        return {
            "metrics": {"latest_fy": fields.get("financial_year")},
            "ratios": {},
            "years": [str(fields.get("financial_year"))] if fields.get("financial_year") else [],
            "trends": {},
            "revenue_growth": [],
            "source": {
                "mode": "structured_annual_report_validation_failed",
                "document": latest.get("original_filename"),
                "financial_year": fields.get("financial_year"),
                "financial_unit": fields.get("financial_unit"),
                "validation_errors": validation_errors,
            },
        }

    # Build trend series from each annual report's current-year statement values
    # instead of scanning one giant text blob for the nearest numbers.
    trend_docs = list(reversed(annual_reports))
    years: List[str] = []
    trends: Dict[str, List[float]] = {
        "Revenue": [], "EBITDA": [], "PAT": [], "Net Worth": [], "Total Debt": [], "CFO": []
    }
    for d in trend_docs:
        f = d.get("extracted_fields") or {}
        mul = _unit_multiplier(f.get("financial_unit"))
        if mul is None:
            continue
        fy = f.get("financial_year")
        if fy:
            years.append(str(fy))
        r = _currency_value(f, "total_income_current", mul)
        if r is None:
            r = _currency_value(f, "revenue_from_operations_current", mul)
        p = _currency_value(f, "profit_after_tax_current", mul)
        nw = _currency_value(f, "total_equity_current", mul)
        cb = _currency_value(f, "current_borrowings_current", mul)
        nb = _currency_value(f, "non_current_borrowings_current", mul)
        td_parts = [x for x in (cb, nb) if x is not None]
        td = sum(td_parts) if td_parts else None
        fpbt = _currency_value(f, "profit_before_tax_current", mul)
        ffi = _currency_value(f, "finance_cost_current", mul)
        fdep = _currency_value(f, "depreciation_amortisation_current", mul)
        febitda = fpbt + ffi + fdep if None not in (fpbt, ffi, fdep) else None
        cfo = _currency_value(f, "net_cash_from_operating_activities_current", mul)
        for name, value in (("Revenue", r), ("EBITDA", febitda), ("PAT", p), ("Net Worth", nw), ("Total Debt", td), ("CFO", cfo)):
            if value is not None:
                trends[name].append(value)
    trends = {k: v for k, v in trends.items() if v}

    revenue_growth = []
    revenue = trends.get("Revenue", [])
    for previous, current in zip(revenue, revenue[1:]):
        if previous not in (None, 0):
            revenue_growth.append((current - previous) / previous * 100)

    return {
        "metrics": metrics,
        "ratios": ratios,
        "years": years,
        "trends": trends,
        "revenue_growth": revenue_growth,
        "source": {
            "mode": "structured_annual_report",
            "document": latest.get("original_filename"),
            "financial_year": fields.get("financial_year"),
            "financial_unit": fields.get("financial_unit"),
        },
    }


def _extract_financial_metrics_legacy(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Legacy free-text fallback kept only for non-annual-report documents."""
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
        metrics = {key: (value * multiplier if value is not None and key != "dscr" else value) for key, value in metrics.items()}

    metrics["current_assets"] = _find_latest(text, ["Current Assets", "Total Current Assets"])
    if metrics["current_assets"] is not None:
        metrics["current_assets"] *= multiplier
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

    return {"metrics": metrics, "ratios": ratios, "years": _find_years(text), "trends": {}, "revenue_growth": [], "source": {"mode": "legacy_text_fallback"}}


def _extract_financial_metrics(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    annual_report_present = any(
        d.get("doc_type") == "annual_report" or (d.get("extracted_fields") or {}).get("document_kind") == "annual_report"
        for d in (documents or [])
    )
    structured = _structured_financial_metrics(documents)
    if structured is not None:
        _fin_debug("financial_path", {"mode": structured.get("source", {}).get("mode"), "annual_report_present": annual_report_present})
        return structured
    if annual_report_present:
        _fin_debug("financial_path", {"mode": "annual_report_present_but_structured_extraction_unavailable", "legacy_fallback_disabled": True})
        return {
            "metrics": {}, "ratios": {}, "years": [], "trends": {}, "revenue_growth": [],
            "source": {"mode": "annual_report_structured_extraction_unavailable", "legacy_fallback_disabled": True},
        }
    legacy = _extract_financial_metrics_legacy(documents)
    _fin_debug("financial_path", {"mode": "legacy_text_fallback", "annual_report_present": False})
    return legacy


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



def _proposal_from_documents(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return the best structured proposal extracted from uploaded evidence.

    The proposal document is authoritative for borrower-requested facility
    terms.  Re-parsing stored text makes this work for sessions uploaded before
    the loan-application extractor was added.
    """
    from app.cam.field_extraction import extract_fields

    candidates: List[Dict[str, Any]] = []
    for d in documents or []:
        fields = dict(d.get("extracted_fields") or {})
        is_proposal = d.get("doc_type") == "loan_application" or fields.get("document_kind") == "loan_application"
        if not is_proposal:
            continue
        if d.get("extracted_text"):
            reparsed = extract_fields("loan_application", d.get("extracted_text") or "")
            if reparsed.get("facility_type") or reparsed.get("requested_amount_cr") is not None:
                fields.update(reparsed)
        if fields:
            candidates.append({"fields": fields, "filename": d.get("original_filename")})

    if not candidates:
        return {}
    # Prefer the candidate with the greatest number of core proposal fields.
    core = ("facility_type", "requested_amount_cr", "purpose", "tenure_months", "repayment", "pricing")
    candidates.sort(key=lambda c: sum(c["fields"].get(k) not in (None, "") for k in core), reverse=True)
    best = dict(candidates[0]["fields"])
    best["source_document"] = candidates[0].get("filename")
    return best

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

    document_proposal = _proposal_from_documents(documents)

    context = build_loan_summary_context(
        state=state,
        metrics=metrics,
        ratios=ratios,
        mca=mca,
        risk_flags=risk_flags,
        collateral_fields=collateral_fields,
        external_data=external_data,
        public_information=public_information,
        document_proposal=document_proposal,
    )
    _fin_debug("loan_summary_context_financials", {
        "financial_source": financial.get("source"),
        "metrics_rupees": metrics,
        "ratios": ratios,
        "context_financials_crore": context.get("financials"),
        "context_ratios": context.get("ratios"),
    })

    borrower = context["borrower"]
    proposal = context["proposal"]
    financials = context["financials"]
    clean_ratios = context["ratios"]
    credit = context["credit"]
    risk = context["risk"]
    collateral = context["collateral"]
    compliance = context["compliance"]

    # Deterministic Step-5 risk observations. Groq can explain these, but does
    # not assign the status or invent the underlying metric.
    derived_risks = list(risk.get("major_risks") or [])
    derived_mitigants = list(risk.get("mitigants") or [])
    if clean_ratios.get("quick_ratio") is not None and clean_ratios.get("quick_ratio") < 1:
        derived_risks.append(f"Quick ratio is {clean_ratios.get('quick_ratio'):.2f}x, indicating reliance on inventory/current-asset conversion.")
    if clean_ratios.get("current_ratio") is not None and clean_ratios.get("current_ratio") < 1.25:
        derived_risks.append(f"Current ratio is {clean_ratios.get('current_ratio'):.2f}x, leaving a limited short-term liquidity cushion.")
    if financials.get("total_debt_cr") is None:
        derived_risks.append("Total debt and leverage assessment are pending because borrowings are not yet available in the normalized evidence.")
    if proposal.get("requested_amount_cr") is not None and financials.get("net_worth_cr") not in (None, 0):
        if proposal.get("requested_amount_cr") / financials.get("net_worth_cr") >= 0.5:
            derived_risks.append(f"Fresh proposed exposure of ₹{proposal.get('requested_amount_cr'):.2f} Cr is material relative to net worth of ₹{financials.get('net_worth_cr'):.2f} Cr.")
    if financials.get("pat_cr") is not None and financials.get("pat_cr") > 0:
        derived_mitigants.append(f"Profitable operations with PAT of ₹{financials.get('pat_cr'):.2f} Cr in {financials.get('latest_fy') or 'the latest period'}.")
    if clean_ratios.get("icr") is not None and clean_ratios.get("icr") >= 2:
        derived_mitigants.append(f"Interest coverage of {clean_ratios.get('icr'):.2f}x provides a debt-service cushion at current finance cost.")
    if financials.get("net_worth_cr") is not None and financials.get("net_worth_cr") > 0:
        derived_mitigants.append(f"Positive net worth of ₹{financials.get('net_worth_cr'):.2f} Cr.")
    risk["major_risks"] = list(dict.fromkeys(derived_risks))
    risk["mitigants"] = list(dict.fromkeys(derived_mitigants))

    uploaded_doc_types = [d.get("doc_type") for d in documents if d.get("doc_type")]
    readiness_profile = "corporate" if borrower.get("cin") else (proposal.get("facility_type") or state.get("loan_type") or "msme")
    progress = compute_progress(readiness_profile, uploaded_doc_types)
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

    presentation = build_presentation(context, readiness, public_information)
    readiness["document_processing_score"] = readiness.get("score")
    readiness["data_readiness_score"] = (presentation.get("data_readiness") or {}).get("score")
    _ls_debug("presentation_context", {
        "borrower": borrower,
        "proposal": proposal,
        "financials": financials,
        "ratios": clean_ratios,
        "credit": credit,
        "risk": risk,
        "collateral": collateral,
        "compliance": compliance,
        "public_information": public_information,
        "readiness": readiness,
        "presentation": presentation,
    })

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
            _ls_debug("groq_input_context", context)
            ai_summary = generate_loan_summary_narrative(context)
            _ls_debug("groq_output", {"raw": ai_summary})
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

    debug_payload = {
        "enabled": FIN_DEBUG,
        "financial_source": financial.get("source") or {},
        "document_types": [
            {
                "file": d.get("original_filename"),
                "doc_type": d.get("doc_type"),
                "financial_year": (d.get("extracted_fields") or {}).get("financial_year"),
                "financial_unit": (d.get("extracted_fields") or {}).get("financial_unit"),
            }
            for d in (documents or [])
        ],
        "metrics_rupees": metrics,
        "ratios_pre_context": ratios,
        "financials_crore": financials,
        "ratios_final": clean_ratios,
        "credit": credit,
        "risk": risk,
        "collateral": collateral,
        "compliance": compliance,
        "public_information": public_information,
        "readiness": readiness,
        "presentation": presentation,
    }
    _fin_debug("final_loan_summary_financial_payload", debug_payload)

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
        "presentation": presentation,
        "debug": {
            "financial_pipeline": debug_payload,
            "loan_summary": {
                "context": context,
                "presentation": presentation,
                "readiness": readiness,
                "llm_status": llm_status,
            },
        } if (FIN_DEBUG or LS_DEBUG) else {},
        "activities": presentation.get("verification_status") or [],
    }

