import os
from typing import Any, Dict, List
from app.cam.web_search import google_search


def _items(value: Dict[str, Any], category: str) -> List[Dict[str, Any]]:
    if not value:
        return []
    if isinstance(value.get("items"), list):
        return value["items"]
    if isinstance(value.get("results"), list):
        return value["results"]
    item = dict(value)
    item.setdefault("category", category)
    return [item]


def _mock(external_data: Dict[str, Any]) -> Dict[str, Any]:
    data = external_data.get("mock_public") or {}
    return {
        "mode": "mock",
        "recent_developments": _items(data.get("company_news") or {}, "company_news"),
        "credit_rating": data.get("credit_rating") or {},
        "industry_observations": _items(data.get("industry_news") or {}, "industry"),
        "adverse_news": _items(data.get("adverse_media") or {}, "adverse_media"),
        "sources": [],
        "note": "Synthetic public-information feed for CAM POC testing.",
    }


def _google(company_name: str, industry: str = "") -> Dict[str, Any]:
    queries = [
        ("company_news", f'"{company_name}" latest company news India'),
        ("credit_rating", f'"{company_name}" CRISIL ICRA CARE India Ratings credit rating'),
        ("adverse_media", f'"{company_name}" fraud default insolvency litigation regulatory action'),
    ]
    if industry:
        queries.append(("industry", f'{industry} India latest industry outlook growth risks'))
    grouped, sources, errors = {}, [], []
    for category, query in queries:
        try:
            results = google_search(query, num_results=4)
        except Exception as exc:
            errors.append(f"{category}: {exc}")
            continue
        grouped[category] = []
        for result in results:
            row = {**result, "category": category, "query": query}
            grouped[category].append(row)
            sources.append({"title": row.get("title"), "url": row.get("url"), "category": category})
    return {
        "mode": "google",
        "recent_developments": grouped.get("company_news", []),
        "credit_rating_search": grouped.get("credit_rating", []),
        "industry_observations": grouped.get("industry", []),
        "adverse_news": grouped.get("adverse_media", []),
        "sources": sources,
        "errors": errors,
        "note": "Public search is supporting evidence and should be independently verified before credit use.",
    }



def _lactose_public_reference(company_name: str) -> Dict[str, Any]:
    if "lactose" not in str(company_name or "").lower():
        return {}
    return {
        "mode": "public_reference_poc",
        "credit_rating": {"agency": "CRISIL", "rating": "BBB-", "outlook": "Stable", "as_of": "10-Jul-2026"},
        "rated_facilities_cr": 90.0,
        "listed_status": "BSE Listed",
        "recent_developments": [{"title": "Rating reaffirmed; rated bank facilities enhanced", "source": "CRISIL public rationale"}],
        "industry_observations": [{"title": "Lactose, lactulose and pharmaceutical manufacturing", "source": "Company / public disclosures"}],
        "adverse_news": [],
        "sources": [
            {"title": "CRISIL rating rationale", "category": "credit_rating"},
            {"title": "Lactose India public filings", "category": "company_filings"},
        ],
        "note": "POC public-reference data. Refresh from live public sources before credit use.",
    }


def collect_public_information(state: Dict[str, Any], external_data: Dict[str, Any], industry: str = "") -> Dict[str, Any]:
    mode = os.getenv("PUBLIC_SEARCH_MODE", "mock").strip().lower() or "mock"
    if mode == "off":
        return {"mode": "off", "recent_developments": [], "industry_observations": [], "adverse_news": [], "sources": []}
    if mode == "google":
        return _google(state.get("company_name") or "", industry)
    mock_data = _mock(external_data)
    if not mock_data.get("credit_rating") and not mock_data.get("recent_developments"):
        lactose = _lactose_public_reference(state.get("company_name") or "")
        if lactose:
            return lactose
    return mock_data
