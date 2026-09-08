"""Deterministic financial analysis and stress testing for CAM Point 4.

Numbers are calculated in Python from normalized/extracted financial facts.  The
optional LLM is used only to turn those already-calculated facts into concise
commentary; it never calculates a ratio or decides whether a threshold passes.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.cam.loan_summary import build_loan_summary
from app.cam.llm_gateway import chat as llm_chat, LLMGatewayError


BENCHMARKS = {
    "current_ratio": {"label": "Current Ratio", "op": "gte", "threshold": 1.25, "display": "≥ 1.25"},
    "quick_ratio": {"label": "Quick Ratio", "op": "gte", "threshold": 1.00, "display": "≥ 1.00"},
    "debt_equity": {"label": "Debt / Equity", "op": "lte", "threshold": 3.00, "display": "≤ 3.00"},
    "tol_tnw": {"label": "TOL / TNW", "op": "lte", "threshold": 4.00, "display": "≤ 4.00"},
    "ebitda_margin": {"label": "EBITDA Margin", "op": "gte", "threshold": 10.0, "display": "≥ 10%", "unit": "%"},
    "pat_margin": {"label": "PAT Margin", "op": "gte", "threshold": 5.0, "display": "≥ 5%", "unit": "%"},
    "roce": {"label": "ROCE", "op": "gte", "threshold": 12.0, "display": "≥ 12%", "unit": "%"},
    "roe": {"label": "ROE", "op": "gte", "threshold": 10.0, "display": "≥ 10%", "unit": "%"},
    "interest_coverage": {"label": "Interest Coverage", "op": "gte", "threshold": 1.50, "display": "≥ 1.50"},
    "dscr": {"label": "DSCR", "op": "gte", "threshold": 1.20, "display": "≥ 1.20"},
}


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _money_cr(value: Any) -> Optional[float]:
    n = _num(value)
    return round(n / 10_000_000, 2) if n is not None else None


def _pct_change(previous: Any, current: Any) -> Optional[float]:
    a, b = _num(previous), _num(current)
    if a in (None, 0) or b is None:
        return None
    return round((b - a) / abs(a) * 100, 1)


def _status(value: Optional[float], rule: Dict[str, Any]) -> str:
    if value is None:
        return "Unavailable"
    passed = value >= rule["threshold"] if rule["op"] == "gte" else value <= rule["threshold"]
    return "Pass" if passed else "Review"


def _format_ratio(value: Optional[float], unit: str = "x") -> str:
    if value is None:
        return "—"
    return f"{value:.2f}%" if unit == "%" else f"{value:.2f}x"


def _latest_series(trend: Dict[str, List[Any]], name: str) -> List[float]:
    return [float(x) for x in (trend.get(name) or []) if _num(x) is not None]


def _derive_ratios(metrics: Dict[str, Any], ratios: Dict[str, Any]) -> Dict[str, Optional[float]]:
    result: Dict[str, Optional[float]] = {}
    aliases = {
        "current_ratio": ["current_ratio", "current_ratio_calculated"],
        "quick_ratio": ["quick_ratio"],
        "debt_equity": ["debt_equity"],
        "ebitda_margin": ["ebitda_margin", "ebitda_margin_calculated"],
        "pat_margin": ["pat_margin", "pat_margin_calculated"],
        "roce": ["roce"],
        "interest_coverage": ["interest_coverage", "interest_coverage_calculated"],
        "dscr": ["dscr"],
    }
    for key, candidates in aliases.items():
        result[key] = next((_num(ratios.get(c)) for c in candidates if _num(ratios.get(c)) is not None), None)

    debt = _num(metrics.get("total_debt"))
    current_liabilities = _num(metrics.get("current_liabilities"))
    nw = _num(metrics.get("net_worth"))
    result["tol_tnw"] = round(((debt or 0) + (current_liabilities or 0)) / nw, 2) if nw not in (None, 0) and (debt is not None or current_liabilities is not None) else None

    pat = _num(metrics.get("pat"))
    result["roe"] = round(pat / nw * 100, 2) if pat is not None and nw not in (None, 0) else None
    return result


def _kpis(metrics: Dict[str, Any], trend: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    defs = [
        ("Revenue", "total_revenue", "Revenue"),
        ("EBITDA", "ebitda", "EBITDA"),
        ("PAT", "pat", "PAT"),
        ("Net Worth", "net_worth", "Net Worth"),
        ("Total Debt", "total_debt", "Total Debt"),
    ]
    out = []
    for label, metric_key, trend_key in defs:
        series = _latest_series(trend, trend_key)
        latest = series[-1] if series else _num(metrics.get(metric_key))
        change = _pct_change(series[-2], series[-1]) if len(series) >= 2 else None
        out.append({"label": label, "value_cr": _money_cr(latest), "change_pct": change})
    return out


def _trend_payload(years: List[str], trend: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    out = []
    for label in ("Revenue", "EBITDA", "PAT"):
        series = _latest_series(trend, label)
        if not series:
            continue
        used_years = years[-len(series):] if years else [f"P{i+1}" for i in range(len(series))]
        out.append({"label": label, "years": used_years, "values_cr": [_money_cr(x) for x in series]})
    return out


def _movement_rows(years: List[str], trend: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    rows = []
    observations = {
        "Revenue": "Operating scale movement versus previous reported period.",
        "EBITDA": "Operating earnings movement versus previous reported period.",
        "PAT": "Bottom-line movement versus previous reported period.",
        "Receivables": "Working-capital collection movement.",
        "Inventory": "Inventory movement versus previous period.",
        "Total Debt": "Borrowing movement versus previous reported period.",
    }
    for label in ("Revenue", "EBITDA", "PAT", "Receivables", "Inventory", "Total Debt"):
        series = _latest_series(trend, label)
        if len(series) < 2:
            continue
        change = _pct_change(series[-2], series[-1])
        severity = "review" if change is not None and abs(change) >= 20 else "normal"
        rows.append({
            "metric": label,
            "previous_cr": _money_cr(series[-2]),
            "current_cr": _money_cr(series[-1]),
            "change_pct": change,
            "severity": severity,
            "observation": observations.get(label, "Material movement calculated from extracted periods."),
        })
    return rows


def _stress(metrics: Dict[str, Any], derived: Dict[str, Optional[float]]) -> List[Dict[str, Any]]:
    revenue = _num(metrics.get("total_revenue"))
    ebitda = _num(metrics.get("ebitda"))
    debt = _num(metrics.get("total_debt"))
    base_dscr = derived.get("dscr")
    base_icr = derived.get("interest_coverage")

    scenarios = [
        {"name": "Base Case", "revenue_factor": 1.00, "ebitda_factor": 1.00, "coverage_factor": 1.00, "label": "Comfortable"},
        {"name": "Moderate Stress", "revenue_factor": 0.90, "ebitda_factor": 0.76, "coverage_factor": 0.81, "label": "Watch"},
        {"name": "Severe Stress", "revenue_factor": 0.80, "ebitda_factor": 0.52, "coverage_factor": 0.58, "label": "Stressed"},
    ]
    out = []
    for s in scenarios:
        stressed_ebitda = ebitda * s["ebitda_factor"] if ebitda is not None else None
        dscr = base_dscr * s["coverage_factor"] if base_dscr is not None else None
        icr = base_icr * s["coverage_factor"] if base_icr is not None else None
        debt_ebitda = debt / stressed_ebitda if debt is not None and stressed_ebitda not in (None, 0) else None
        status = s["label"]
        if dscr is not None:
            status = "Comfortable" if dscr >= 1.20 else "Watch" if dscr >= 1.0 else "Stressed"
        out.append({
            "scenario": s["name"],
            "revenue_cr": _money_cr(revenue * s["revenue_factor"] if revenue is not None else None),
            "ebitda_cr": _money_cr(stressed_ebitda),
            "interest_coverage": round(icr, 2) if icr is not None else None,
            "dscr": round(dscr, 2) if dscr is not None else None,
            "debt_ebitda": round(debt_ebitda, 2) if debt_ebitda is not None else None,
            "assessment": status,
            "assumptions": {
                "revenue_change_pct": round((s["revenue_factor"] - 1) * 100),
                "ebitda_factor": s["ebitda_factor"],
            },
        })
    return out


def _deterministic_commentary(kpis, ratio_rows, movements, stress_rows) -> Dict[str, List[str]]:
    comments = {"financial_performance": [], "liquidity_working_capital": [], "leverage_coverage": [], "stress_testing": []}
    for item in kpis[:3]:
        if item.get("change_pct") is not None:
            direction = "increased" if item["change_pct"] >= 0 else "declined"
            comments["financial_performance"].append(f"{item['label']} {direction} by {abs(item['change_pct']):.1f}% versus the previous reported period.")
    for r in ratio_rows:
        if r["key"] in ("current_ratio", "quick_ratio") and r["value"] is not None:
            comments["liquidity_working_capital"].append(f"{r['label']} is {r['display_value']} ({r['status'].lower()} against configured benchmark).")
        if r["key"] in ("debt_equity", "interest_coverage", "dscr") and r["value"] is not None:
            comments["leverage_coverage"].append(f"{r['label']} is {r['display_value']} ({r['status'].lower()} against configured benchmark).")
    for m in movements:
        if m.get("severity") == "review":
            comments["liquidity_working_capital"].append(f"{m['metric']} moved {abs(m['change_pct']):.1f}% and merits review as a material movement.")
    for row in stress_rows[1:]:
        if row.get("dscr") is not None:
            comments["stress_testing"].append(f"Under {row['scenario'].lower()}, projected DSCR is {row['dscr']:.2f}x and the scenario is assessed as {row['assessment'].lower()}.")
    for key in comments:
        if not comments[key]:
            comments[key].append("Insufficient structured data is available for a specific observation in this area.")
    return comments


def _ai_commentary(base: Dict[str, List[str]], compact_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Optional narrative polishing; deterministic comments remain available on failure."""
    try:
        content = llm_chat([
            {"role": "system", "content": "You are a bank CAM financial analyst. Use ONLY the supplied calculated facts. Never calculate, infer or invent a number. Return JSON with four arrays: financial_performance, liquidity_working_capital, leverage_coverage, stress_testing. Each array: max 3 concise observations."},
            {"role": "user", "content": json.dumps(compact_payload, ensure_ascii=False)},
        ], temperature=0.1, response_format={"type": "json_object"})
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            cleaned = {}
            for key in base:
                vals = parsed.get(key)
                cleaned[key] = [str(x) for x in vals[:3]] if isinstance(vals, list) and vals else base[key]
            return {"source": "ai_generated", "sections": cleaned, "error": ""}
    except (LLMGatewayError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {"source": "deterministic", "sections": base, "error": str(exc)}
    return {"source": "deterministic", "sections": base, "error": "AI commentary was unavailable."}


def build_financial_analysis(state: Dict[str, Any], documents: List[Dict[str, Any]], include_ai: bool = True) -> Dict[str, Any]:
    summary = build_loan_summary(state, documents)
    metrics = summary.get("financial_metrics_raw") or {}
    ratios = summary.get("ratios") or {}
    trend = dict(summary.get("financial_trend") or {})
    years = summary.get("financial_years") or []

    # Add extracted single-series values when they exist in metrics but were not parsed as trends.
    for label, metric_key in (("Inventory", "inventory"), ("Receivables", "receivables")):
        if label not in trend and metrics.get(metric_key) is not None:
            trend[label] = [metrics[metric_key]]

    derived = _derive_ratios(metrics, ratios)
    ratio_rows = []
    for key, rule in BENCHMARKS.items():
        value = derived.get(key)
        ratio_rows.append({
            "key": key,
            "label": rule["label"],
            "value": round(value, 2) if value is not None else None,
            "display_value": _format_ratio(value, rule.get("unit", "x")),
            "benchmark": rule["display"],
            "status": _status(value, rule),
        })

    kpis = _kpis(metrics, trend)
    trends = _trend_payload(years, trend)
    movements = _movement_rows(years, trend)
    stress_rows = _stress(metrics, derived)
    base_comments = _deterministic_commentary(kpis, ratio_rows, movements, stress_rows)
    commentary = {"source": "deterministic", "sections": base_comments, "error": ""}
    if include_ai:
        commentary = _ai_commentary(base_comments, {
            "kpis": kpis,
            "ratios": ratio_rows,
            "material_movements": movements,
            "stress_testing": stress_rows,
        })

    sources = []
    for d in documents or []:
        dtype = str(d.get("doc_type") or d.get("document_type") or "").lower()
        if any(x in dtype for x in ("balance", "profit", "financial", "bank_statement", "itr", "gstr")):
            sources.append({"name": d.get("original_filename") or "Financial document", "type": d.get("display_name") or dtype.replace("_", " ").title()})

    return {
        "company_name": state.get("company_name") or state.get("company") or "Borrower",
        "cam_id": state.get("cam_id"),
        "years": years,
        "latest_year": years[-1] if years else "Latest available",
        "kpis": kpis,
        "ratios": ratio_rows,
        "trends": trends,
        "material_movements": movements,
        "stress_testing": stress_rows,
        "commentary": commentary,
        "sources": sources,
        "methodology": "Ratios, movements and stress outputs are deterministic Python calculations from extracted financial evidence. AI is used only to phrase commentary.",
    }
