from __future__ import annotations

import re
from typing import Any, Dict, List

from app.cam.borrower_info import build_borrower_profile
from app.cam.loan_summary import _extract_financial_metrics
from app.cam.loan_summary_service.external_data_service import collect_external_data
from app.cam.loan_summary_service.public_search_service import collect_public_information
from .ai_enrichment import build_ai_business_overview


def _value(item):
    return item.get("value") if isinstance(item, dict) and "value" in item else item


def _first(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _field(documents: List[Dict[str, Any]], candidates: List[str]):
    wanted = {re.sub(r"[^a-z0-9]", "", x.lower()) for x in candidates}
    for doc in documents or []:
        for key, value in (doc.get("extracted_fields") or {}).items():
            norm = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if norm in wanted and value not in (None, ""):
                return value, doc.get("original_filename") or doc.get("display_name") or "Uploaded document"
    return None, None


def _list_value(value):
    if value in (None, "", [], {}):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return [x.strip() for x in re.split(r"[,;|\n]+", str(value)) if x.strip()]


def _crore(value):
    try:
        return round(float(value) / 10_000_000, 2)
    except Exception:
        return None


def _growth_pct(series):
    if not series or len(series) < 2:
        return None
    try:
        a, b = float(series[-2]), float(series[-1])
        return round((b - a) / a * 100, 2) if a else None
    except Exception:
        return None


def _cagr_pct(series):
    if not series or len(series) < 2:
        return None
    try:
        start, end = float(series[0]), float(series[-1])
        periods = len(series) - 1
        if start <= 0 or end < 0 or periods <= 0:
            return None
        return round(((end / start) ** (1 / periods) - 1) * 100, 2)
    except Exception:
        return None


def _source(name, source_type, status="fetched", detail=None):
    return {"name": name, "source_type": source_type, "status": status, "detail": detail}


def build_business_overview(state: Dict[str, Any], documents: List[Dict[str, Any]], include_ai: bool = True) -> Dict[str, Any]:
    external = collect_external_data(state)
    api = external.get("api") or {}
    derived = external.get("derived") or {}
    mock_ctx = derived.get("loan_summary_context") or {}
    mock_borrower = mock_ctx.get("borrower") or {}
    mock_risk = mock_ctx.get("risk") or {}
    mock_fin = mock_ctx.get("financials") or {}

    borrower = build_borrower_profile(state, documents, include_ai=False)
    corp = borrower.get("corporate_profile") or {}
    borrower_business = borrower.get("business_profile") or {}
    geography = borrower.get("geography") or {}

    industry_api = api.get("industry_peer_response") or {}
    industry = _first(
        (corp.get("industry") or {}).get("value") if isinstance(corp.get("industry"), dict) else None,
        _value(borrower_business.get("industry")),
        industry_api.get("industry"),
        mock_borrower.get("industry"),
    )
    public = collect_public_information(state, external, str(industry or ""))
    financial = _extract_financial_metrics(documents)
    trends = financial.get("trends") or {}
    years = financial.get("years") or []
    revenue_series = trends.get("Revenue") or []
    pat_series = trends.get("PAT") or []

    if not revenue_series and mock_fin.get("revenue_cr") is not None:
        revenue_series = [float(mock_fin["revenue_cr"]) * 10_000_000]
    if not pat_series and mock_fin.get("pat_cr") is not None:
        pat_series = [float(mock_fin["pat_cr"]) * 10_000_000]

    business_desc, business_desc_source = _field(documents, [
        "business_description", "nature_of_business", "line_of_business", "principal_business_activity", "business_activity"
    ])
    product_value, product_source = _field(documents, ["products", "key_products", "products_services", "product_services"])
    customer_value, customer_source = _field(documents, ["customer_segments", "key_customers", "customer_profile", "major_customers"])
    supplier_value, supplier_source = _field(documents, ["key_suppliers", "supplier_profile", "major_suppliers", "raw_materials"])
    capacity_value, capacity_source = _field(documents, ["capacity_utilisation", "capacity_utilization", "installed_capacity"])

    business_type = _first(
        borrower_business.get("business_type"),
        (corp.get("constitution") or {}).get("value") if isinstance(corp.get("constitution"), dict) else None,
        "Manufacturing" if industry and "manufactur" in str(industry).lower() else None,
    )
    if business_type and "private limited" in str(business_type).lower():
        business_type = "Manufacturing" if industry and "manufactur" in str(industry).lower() else "Operating company"

    business_model = {
        "type": business_type,
        "industry": industry,
        "description": _first(business_desc, _value(borrower_business.get("description")), _value(borrower_business.get("line_of_business"))),
        "revenue_model": _value(borrower_business.get("revenue_model")),
        "customer_model": _value(borrower_business.get("customer_model")),
        "source": business_desc_source or "Borrower profile / external data",
    }

    products_services = []
    for value in _list_value(product_value):
        products_services.append({"name": value, "source": product_source or "Uploaded document"})

    customer_segments = []
    for value in _list_value(customer_value):
        customer_segments.append({"segment": value, "source": customer_source or "Uploaded document"})

    suppliers = []
    for value in _list_value(supplier_value):
        suppliers.append({"name": value, "source": supplier_source or "Uploaded document"})

    footprint = {
        "registered_office": _value(corp.get("registered_office")) or _value(geography.get("registered_office")),
        "plants": geography.get("plants") or [],
        "branches": geography.get("branches") or [],
        "operating_states": geography.get("operating_states") or [],
        "export_markets": geography.get("export_markets") or [],
        "capacity": capacity_value,
        "capacity_source": capacity_source,
    }

    chart = []
    max_len = max(len(years), len(revenue_series), len(pat_series))
    for i in range(max_len):
        chart.append({
            "year": years[i] if i < len(years) else (f"Period {i+1}" if max_len > 1 else "Latest"),
            "revenue_cr": _crore(revenue_series[i]) if i < len(revenue_series) else None,
            "pat_cr": _crore(pat_series[i]) if i < len(pat_series) else None,
        })

    latest_revenue_cr = _crore(revenue_series[-1]) if revenue_series else mock_fin.get("revenue_cr")
    revenue_profile = {
        "latest_revenue_cr": latest_revenue_cr,
        "latest_pat_cr": _crore(pat_series[-1]) if pat_series else mock_fin.get("pat_cr"),
        "latest_growth_pct": _growth_pct(revenue_series),
        "cagr_pct": _cagr_pct(revenue_series),
        "trend": chart,
        "segment_mix": [],
        "note": "Revenue and PAT are taken from uploaded financial evidence where available; no segment mix is estimated when unavailable.",
    }

    company_structure = {
        "ownership": borrower.get("ownership") or {},
        "promoters_directors": borrower.get("promoters_directors") or [],
        "group_relationship": (borrower.get("ownership") or {}).get("group_relationship") if isinstance(borrower.get("ownership"), dict) else None,
    }

    rating = public.get("credit_rating") or {}
    market_position = {
        "industry": industry,
        "industry_growth_pct": industry_api.get("industry_growth_pct"),
        "industry_median_ebitda_margin_pct": industry_api.get("industry_median_ebitda_margin_pct"),
        "borrower_ebitda_margin_pct": industry_api.get("borrower_ebitda_margin_pct"),
        "credit_rating": _first(rating.get("rating"), rating.get("current_rating")),
        "outlook": rating.get("outlook"),
        "positioning_note": "No market-share or leadership claim is made unless supported by a source.",
    }

    strengths = []
    latest_growth = revenue_profile.get("latest_growth_pct")
    cagr = revenue_profile.get("cagr_pct")
    if latest_growth is not None and latest_growth > 0:
        strengths.append(f"Latest revenue growth is {latest_growth:.1f}% based on available financial evidence")
    if cagr is not None and cagr > 0:
        strengths.append(f"Revenue CAGR across available periods is {cagr:.1f}%")
    if industry_api.get("borrower_ebitda_margin_pct") and industry_api.get("industry_median_ebitda_margin_pct"):
        if float(industry_api["borrower_ebitda_margin_pct"]) >= float(industry_api["industry_median_ebitda_margin_pct"]):
            strengths.append("EBITDA margin is at or above the available synthetic industry median")

    business_risks = list(mock_risk.get("major_risks") or [])
    if not customer_segments:
        business_risks.append("Customer-segment detail is not available from current structured evidence")
    if not products_services:
        business_risks.append("Detailed product/service mix is not available from current structured evidence")
    business_risks = list(dict.fromkeys(business_risks))

    recent_developments = public.get("recent_developments") or []
    sources = [
        _source("Borrower Information", "Normalized CAM profile", "validated"),
        _source("Uploaded Documents", "Document extraction", "processed", f"{len(documents)} documents"),
    ]
    if external.get("mock_matched"):
        sources.append(_source("External Company Data", "Synthetic POC provider", "fetched"))
    if state.get("mca"):
        sources.append(_source("MCA / FileSure", "Corporate registry", "official_source"))
    if public.get("mode") != "off":
        sources.append(_source("Public Information", f"Public search ({public.get('mode')})", "fetched"))

    context = {
        "company_name": state.get("company_name") or borrower.get("company_name"),
        "business_model": business_model,
        "products_services": products_services,
        "customer_profile": {"segments": customer_segments, "concentration": None},
        "supplier_profile": {"suppliers_or_inputs": suppliers},
        "operating_footprint": footprint,
        "company_structure": company_structure,
        "revenue_profile": revenue_profile,
        "market_position": market_position,
        "strengths": strengths,
        "business_risks": business_risks,
        "recent_developments": recent_developments,
        "industry_observations": public.get("industry_observations") or [],
        "sources": sources,
        "data_note": "Business Overview is source-grounded. Missing products, customers, capacity or market-share data is left unavailable rather than estimated.",
    }

    if include_ai:
        ai = build_ai_business_overview(context)
        context["ai_overview"] = ai.get("text")
        context["ai_overview_source"] = ai.get("source")
        context["llm_status"] = ai.get("llm_status")
    return context
