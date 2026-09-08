"""CAM Point 10 — Industry Overview, Market Analysis & Peer Benchmarking.

Point 10 is intentionally computed after collateral (Point 7) and before the
final consolidated risk refresh / proposed loan terms.  The module consumes
already-normalized CAM outputs plus configured public/market feeds.  It never
invents peer statistics: unavailable peer metrics remain unavailable.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.cam.loan_summary_service.external_data_service import collect_external_data
from app.cam.loan_summary_service.public_search_service import collect_public_information
from app.cam.llm_gateway import chat as llm_chat, LLMGatewayError


def _num(value: Any) -> Optional[float]:
    try:
        if value in (None, "", "—", "N/A", "Not available"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _first(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _ratio_value(financial: Dict[str, Any], key: str) -> Optional[float]:
    row = next((r for r in financial.get("ratios") or [] if r.get("key") == key), None)
    return _num(row.get("value")) if row else None


def _kpi_change(financial: Dict[str, Any], label: str) -> Optional[float]:
    row = next((r for r in financial.get("kpis") or [] if str(r.get("label", "")).lower() == label.lower()), None)
    return _num(row.get("change_pct")) if row else None


def _position(borrower: Optional[float], benchmark: Optional[float], higher_is_better: bool = True) -> str:
    if borrower is None or benchmark is None:
        return "Not available"
    tolerance = max(abs(benchmark) * 0.08, 0.25)
    delta = borrower - benchmark
    if abs(delta) <= tolerance:
        return "In Line"
    better = delta > 0 if higher_is_better else delta < 0
    return "Better" if better else "Weaker"


def _display(value: Optional[float], unit: str = "%") -> str:
    if value is None:
        return "—"
    if unit == "x":
        return f"{value:.2f}x"
    return f"{value:.1f}%"


def _public_text(items: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        for key in ("title", "snippet", "description", "text", "summary"):
            if item.get(key):
                parts.append(str(item[key]))
    return " ".join(parts).lower()


def _market_factors(growth: Optional[float], public: Dict[str, Any]) -> List[Dict[str, str]]:
    text = _public_text(public.get("industry_observations") or [])

    demand = "Not assessed"
    if growth is not None:
        demand = "Positive" if growth >= 5 else "Stable" if growth >= 0 else "Weak"

    competition = "Not assessed"
    if any(x in text for x in ("competitive", "competition", "price war", "fragmented")):
        competition = "High"

    input_cost = "Not assessed"
    if any(x in text for x in ("raw material", "commodity", "input cost", "freight", "energy cost")):
        input_cost = "Watch"

    regulatory = "Not assessed"
    if any(x in text for x in ("regulation", "regulatory", "compliance", "government policy", "tariff", "duty")):
        regulatory = "Watch"

    pricing = "Not assessed"
    if any(x in text for x in ("pricing power", "price increase", "margin pressure", "price pressure")):
        pricing = "Moderate"

    return [
        {"factor": "Demand Outlook", "assessment": demand},
        {"factor": "Competition", "assessment": competition},
        {"factor": "Pricing Power", "assessment": pricing},
        {"factor": "Input Cost Pressure", "assessment": input_cost},
        {"factor": "Regulatory Risk", "assessment": regulatory},
    ]


def _base_commentary(company: str, industry: str, peer_rows: List[Dict[str, Any]], strengths: List[str], risks: List[str]) -> str:
    assessed = [r for r in peer_rows if r.get("position") != "Not available"]
    stronger = sum(1 for r in assessed if r.get("position") == "Better")
    weaker = sum(1 for r in assessed if r.get("position") == "Weaker")
    parts = [f"{company} has been assessed in the context of {industry or 'its identified industry'} using available market and peer evidence."]
    if assessed:
        parts.append(f"Of {len(assessed)} benchmarked indicators, {stronger} are stronger than the available benchmark and {weaker} are weaker.")
    else:
        parts.append("Structured peer benchmarks are limited, so unavailable metrics have not been estimated.")
    if strengths:
        parts.append("Relative strengths include " + " ".join(strengths[:2]))
    if risks:
        parts.append("Key market/peer considerations include " + " ".join(risks[:2]))
    parts.append("This section is analytical context only and is not a sanction recommendation.")
    return " ".join(parts)


def _ai_commentary(base: str, compact: Dict[str, Any]) -> Dict[str, str]:
    try:
        content = llm_chat([
            {"role": "system", "content": "You are a bank CAM industry analyst. Use ONLY supplied facts. Do not invent market share, peer names, growth rates or benchmarks. Return JSON with one field commentary, maximum 180 words. Explain relative positioning, industry outlook and material risks. State that unavailable metrics were not estimated and that the output is not a sanction recommendation."},
            {"role": "user", "content": json.dumps(compact, ensure_ascii=False)},
        ], temperature=0.1, response_format={"type": "json_object"})
        parsed = json.loads(content)
        text = str(parsed.get("commentary") or "").strip()
        if text:
            return {"source": "ai_generated", "text": text, "error": ""}
    except (LLMGatewayError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {"source": "deterministic", "text": base, "error": str(exc)}
    return {"source": "deterministic", "text": base, "error": "AI commentary unavailable."}


def build_industry_peer_analysis(state: Dict[str, Any], documents: List[Dict[str, Any]], include_ai: bool = True) -> Dict[str, Any]:
    financial = state.get("financial_analysis_cache") or {}
    business = state.get("business_overview_cache") or {}

    external = collect_external_data(state)
    api = external.get("api") or {}
    peer_api = api.get("industry_peer_response") or {}

    model = business.get("business_model") or {}
    market_position = business.get("market_position") or {}
    industry = _first(
        model.get("industry"),
        market_position.get("industry"),
        peer_api.get("industry"),
        state.get("industry"),
        "Industry not identified",
    )

    public = collect_public_information(state, external, str(industry or ""))
    industry_growth = _num(_first(peer_api.get("industry_growth_pct"), market_position.get("industry_growth_pct")))
    peer_ebitda = _num(_first(peer_api.get("industry_median_ebitda_margin_pct"), market_position.get("industry_median_ebitda_margin_pct")))

    borrower_growth = _kpi_change(financial, "Revenue")
    borrower_ebitda = _ratio_value(financial, "ebitda_margin")
    borrower_de = _ratio_value(financial, "debt_equity")
    borrower_current = _ratio_value(financial, "current_ratio")
    borrower_roce = _ratio_value(financial, "roce")
    borrower_dscr = _ratio_value(financial, "dscr")

    # Optional provider keys are supported when present. Missing values remain unavailable.
    peer_rows = [
        {
            "metric": "Revenue Growth",
            "borrower": _display(borrower_growth),
            "borrower_value": borrower_growth,
            "benchmark": _display(industry_growth),
            "benchmark_value": industry_growth,
            "benchmark_label": "Industry Growth",
            "position": _position(borrower_growth, industry_growth, True),
        },
        {
            "metric": "EBITDA Margin",
            "borrower": _display(borrower_ebitda),
            "borrower_value": borrower_ebitda,
            "benchmark": _display(peer_ebitda),
            "benchmark_value": peer_ebitda,
            "benchmark_label": "Industry Median",
            "position": _position(borrower_ebitda, peer_ebitda, True),
        },
        {
            "metric": "Debt / Equity",
            "borrower": _display(borrower_de, "x"),
            "borrower_value": borrower_de,
            "benchmark": _display(_num(peer_api.get("industry_median_debt_equity")), "x"),
            "benchmark_value": _num(peer_api.get("industry_median_debt_equity")),
            "benchmark_label": "Peer Median",
            "position": _position(borrower_de, _num(peer_api.get("industry_median_debt_equity")), False),
        },
        {
            "metric": "Current Ratio",
            "borrower": _display(borrower_current, "x"),
            "borrower_value": borrower_current,
            "benchmark": _display(_num(peer_api.get("industry_median_current_ratio")), "x"),
            "benchmark_value": _num(peer_api.get("industry_median_current_ratio")),
            "benchmark_label": "Peer Median",
            "position": _position(borrower_current, _num(peer_api.get("industry_median_current_ratio")), True),
        },
        {
            "metric": "ROCE",
            "borrower": _display(borrower_roce),
            "borrower_value": borrower_roce,
            "benchmark": _display(_num(peer_api.get("industry_median_roce_pct"))),
            "benchmark_value": _num(peer_api.get("industry_median_roce_pct")),
            "benchmark_label": "Peer Median",
            "position": _position(borrower_roce, _num(peer_api.get("industry_median_roce_pct")), True),
        },
        {
            "metric": "DSCR",
            "borrower": _display(borrower_dscr, "x"),
            "borrower_value": borrower_dscr,
            "benchmark": _display(_num(peer_api.get("industry_median_dscr")), "x"),
            "benchmark_value": _num(peer_api.get("industry_median_dscr")),
            "benchmark_label": "Peer Median",
            "position": _position(borrower_dscr, _num(peer_api.get("industry_median_dscr")), True),
        },
    ]

    strengths: List[str] = []
    risks: List[str] = []
    for row in peer_rows:
        if row["position"] == "Better":
            strengths.append(f"{row['metric']} is better than the available {row['benchmark_label'].lower()}.")
        elif row["position"] == "Weaker":
            risks.append(f"{row['metric']} is weaker than the available {row['benchmark_label'].lower()}.")

    if industry_growth is not None:
        if industry_growth < 0:
            risks.append(f"Available industry data indicates contraction of {abs(industry_growth):.1f}%.")
        elif industry_growth >= 5:
            strengths.append(f"Available industry growth is {industry_growth:.1f}%.")

    public_industry = public.get("industry_observations") or []
    developments = []
    for item in public_industry[:6]:
        if isinstance(item, dict):
            developments.append({
                "title": item.get("title") or item.get("headline") or "Industry observation",
                "snippet": item.get("snippet") or item.get("description") or item.get("text") or "",
                "url": item.get("url"),
                "source": item.get("source") or item.get("displayLink") or "Public information",
            })

    market_factors = _market_factors(industry_growth, public)
    factors_assessed = [x for x in market_factors if x["assessment"] != "Not assessed"]
    overall_outlook = "Not assessed"
    if industry_growth is not None:
        overall_outlook = "Positive" if industry_growth >= 5 else "Stable" if industry_growth >= 0 else "Weak"

    company = state.get("company_name") or state.get("company") or "Borrower"
    base = _base_commentary(company, str(industry), peer_rows, strengths, risks)
    commentary = {"source": "deterministic", "text": base, "error": ""}
    if include_ai:
        commentary = _ai_commentary(base, {
            "company": company,
            "industry": industry,
            "industry_growth_pct": industry_growth,
            "overall_outlook": overall_outlook,
            "peer_comparison": peer_rows,
            "market_factors": market_factors,
            "strengths": strengths[:5],
            "risks": risks[:5],
            "industry_observations": developments[:4],
        })

    sources = [
        {"name": "Business Overview", "type": "Upstream CAM module", "status": "available" if business else "limited"},
        {"name": "Financial Analysis", "type": "Upstream CAM module", "status": "available" if financial else "limited"},
    ]
    if peer_api:
        sources.append({"name": peer_api.get("provider") or "Industry / Peer Data", "type": "Configured market-data provider", "status": "available"})
    if public.get("mode") and public.get("mode") != "off":
        sources.append({"name": f"Public Information ({public.get('mode')})", "type": "Supporting external evidence", "status": "available" if public_industry else "limited"})

    assessed_count = sum(1 for x in peer_rows if x.get("position") != "Not available")
    return {
        "company_name": company,
        "cam_id": state.get("cam_id"),
        "industry": industry,
        "summary": {
            "industry_growth_pct": industry_growth,
            "overall_outlook": overall_outlook,
            "peer_metrics_assessed": assessed_count,
            "peer_metrics_total": len(peer_rows),
            "relative_strengths": len(strengths),
            "relative_risks": len(risks),
            "market_factors_assessed": len(factors_assessed),
        },
        "industry_overview": {
            "industry": industry,
            "growth_pct": industry_growth,
            "outlook": overall_outlook,
            "industry_median_ebitda_margin_pct": peer_ebitda,
            "data_provider": peer_api.get("provider") or ("Public search" if public_industry else "Not available"),
        },
        "peer_comparison": peer_rows,
        "market_factors": market_factors,
        "strengths": list(dict.fromkeys(strengths))[:8],
        "risks": list(dict.fromkeys(risks))[:8],
        "industry_developments": developments,
        "commentary": commentary,
        "sources": sources,
        "methodology": "Point 10 reuses normalized business and financial outputs and configured market/public evidence. Relative positioning is deterministic. Missing peer metrics are shown as unavailable and are never estimated by AI.",
        "decision_notice": "Industry/peer analysis is supporting credit context only. Final risk assessment and sanction judgement remain with authorised bank officials.",
    }
