from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import re

from app.cam.loan_summary_service.external_data_service import collect_external_data
from app.cam.loan_summary_service.public_search_service import collect_public_information
from .verification import field, verify_exact, verify_name
from .ai_enrichment import build_ai_overview


def _first(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _doc_field(documents: List[Dict[str, Any]], keys: List[str]):
    wanted = {k.lower() for k in keys}
    for doc in documents:
        for key, value in (doc.get("extracted_fields") or {}).items():
            if str(key).lower() in wanted and value not in (None, ""):
                return value
    return None


def _doc_field_with_source(documents: List[Dict[str, Any]], keys: List[str]):
    wanted = {k.lower() for k in keys}
    for doc in documents:
        for key, value in (doc.get("extracted_fields") or {}).items():
            if str(key).lower() in wanted and value not in (None, ""):
                return value, doc.get("original_filename") or doc.get("display_name") or "Uploaded document"
    return None, None


def _years_since(value: Any) -> Optional[int]:
    if not value:
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    if not match:
        return None
    year = int(match.group(0))
    return max(0, date.today().year - year)


def _normalize_real_mca(state: Dict[str, Any]) -> Dict[str, Any]:
    raw = state.get("mca") or {}
    raw = raw.get("data") if isinstance(raw, dict) else raw
    if not isinstance(raw, dict):
        return {}
    payload = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    master = payload.get("masterData") or {}
    company = master.get("companyData") or payload
    addresses = company.get("MCAMDSCompanyAddress") or []
    address = addresses[0] if addresses else {}
    address_text = ", ".join(str(address.get(k)).strip() for k in ("addressLine1", "addressLine2", "city", "state", "pinCode") if address.get(k))
    return {
        "provider": "FileSure / MCA",
        "cin": payload.get("cin") or company.get("cin"),
        "company_name": payload.get("company") or company.get("companyName"),
        "company_status": company.get("companyStatus"),
        "incorporation_date": company.get("dateOfIncorporation"),
        "registered_address": address_text or None,
        "authorized_capital": company.get("authorisedCapital"),
        "paid_up_capital": company.get("paidupCapital"),
        "company_type": company.get("companyType") or company.get("classOfCompany") or company.get("companyCategory"),
        "directors": master.get("directorData") or [],
    }


def _source_row(name, source_type, status, detail=None):
    return {"name": name, "source_type": source_type, "status": status, "detail": detail}


def _public_summary(public: Dict[str, Any]):
    return {
        "mode": public.get("mode"),
        "credit_rating": public.get("credit_rating") or public.get("credit_rating_search") or {},
        "recent_developments": public.get("recent_developments") or [],
        "industry_observations": public.get("industry_observations") or [],
        "adverse_news": public.get("adverse_news") or [],
        "sources": public.get("sources") or [],
        "note": public.get("note"),
    }


def build_borrower_profile(state: Dict[str, Any], documents: List[Dict[str, Any]], *, include_ai: bool = True) -> Dict[str, Any]:
    external = collect_external_data(state)
    api = external.get("api") or {}
    derived = external.get("derived") or {}
    loan_ctx = derived.get("loan_summary_context") or {}
    mock_borrower = loan_ctx.get("borrower") or {}

    real_mca = _normalize_real_mca(state)
    mock_mca = api.get("mca_response") or {}
    mca = real_mca or mock_mca
    gst = api.get("gst_response") or {}
    pan_api = api.get("pan_response") or {}
    udyam = api.get("udyam_response") or {}
    banking = api.get("internal_banking_response") or {}

    doc_cin, doc_cin_source = _doc_field_with_source(documents, ["cin"])
    doc_pan, doc_pan_source = _doc_field_with_source(documents, ["pan", "pan_number", "pan_number_masked"])
    doc_gstin, doc_gstin_source = _doc_field_with_source(documents, ["gstin", "gstin_number", "gst_number"])
    doc_company, doc_company_source = _doc_field_with_source(documents, ["company_name", "legal_name", "trade_name"])
    doc_address, doc_address_source = _doc_field_with_source(documents, ["registered_office", "registered_address", "address"])
    doc_industry, doc_industry_source = _doc_field_with_source(documents, ["industry", "business_industry", "line_of_business"])

    name = _first(mca.get("company_name"), mca.get("name"), state.get("company_name"), mock_borrower.get("name"), doc_company)
    cin = _first(mca.get("cin"), mock_borrower.get("cin"), doc_cin)
    pan = _first(pan_api.get("pan"), mca.get("pan"), doc_pan)
    gstin = _first(gst.get("gstin"), mock_borrower.get("gstin"), doc_gstin)
    incorporation = _first(mca.get("incorporation_date"), mca.get("incorporation_year"), mock_borrower.get("incorporation_year"))
    constitution = _first(mca.get("company_type"), mock_borrower.get("constitution"), state.get("constitution"))
    registered_office = _first(mca.get("registered_address"), ", ".join(x for x in [mca.get("registered_city"), mca.get("registered_state")] if x), doc_address)
    industry = _first(mca.get("industry"), mock_borrower.get("industry"), doc_industry, state.get("industry"))

    cin_check = verify_exact(cin, doc_cin, official=True)
    company_check = verify_name(name, _first(gst.get("legal_name"), pan_api.get("name"), doc_company), official=True)
    pan_check = verify_exact(pan, doc_pan, official=bool(pan_api))
    gst_check = verify_exact(gstin, doc_gstin, official=bool(gst))

    corporate_profile = {
        "company_name": field(name, mca.get("provider") or "MCA / FileSure", company_check["status"], source_type="Official corporate data"),
        "cin": field(cin, mca.get("provider") or "MCA / FileSure", cin_check["status"], source_type="Official corporate data"),
        "constitution": field(constitution, mca.get("provider") or "MCA / FileSure", "official_source" if constitution else "pending"),
        "company_status": field(_first(mca.get("company_status"), mca.get("status")), mca.get("provider") or "MCA / FileSure", "official_source" if mca else "pending"),
        "incorporation_date": field(incorporation, mca.get("provider") or "MCA / FileSure", "official_source" if incorporation else "pending"),
        "business_vintage_years": field(_years_since(incorporation), "Calculated from incorporation date", "validated" if incorporation else "pending"),
        "registered_office": field(registered_office, mca.get("provider") or doc_address_source or "Current evidence", "official_source" if mca and registered_office else ("fetched" if registered_office else "pending")),
        "authorized_capital": field(_first(mca.get("authorized_capital"), mca.get("authorized_capital_cr")), mca.get("provider") or "MCA / FileSure", "official_source" if mca else "pending"),
        "paid_up_capital": field(_first(mca.get("paid_up_capital"), mca.get("paid_up_capital_cr")), mca.get("provider") or "MCA / FileSure", "official_source" if mca else "pending"),
        "industry": field(industry, _first(mca.get("provider"), doc_industry_source, "Borrower profile"), "fetched" if industry else "pending"),
    }

    registration = {
        "pan": field(pan, "PAN API" if pan_api else (doc_pan_source or "Uploaded document"), pan_check["status"]),
        "gstin": field(gstin, "GST API" if gst else (doc_gstin_source or "Uploaded document"), gst_check["status"]),
        "gst_status": field(gst.get("status"), "GST API", "official_source" if gst.get("status") else "pending"),
        "udyam": field(udyam.get("udyam_no"), "Udyam API", "official_source" if udyam.get("udyam_no") else "pending"),
        "udyam_status": field(udyam.get("status"), "Udyam API", "official_source" if udyam.get("status") else "pending"),
    }

    directors = []
    raw_directors = mca.get("directors") or []
    for d in raw_directors:
        name_d = d.get("name") or d.get("directorName") or " ".join(str(d.get(k) or "").strip() for k in ("firstName", "lastName")).strip()
        if name_d:
            directors.append({
                "name": name_d,
                "designation": d.get("designation") or "Director",
                "din": d.get("DIN") or d.get("din"),
                "shareholding_pct": d.get("shareholding_pct"),
                "source": mca.get("provider") or "MCA / FileSure",
                "status": "official_source",
            })

    shareholding = _doc_field(documents, ["shareholding", "promoter_shareholding", "promoter_holding"])
    ownership = {
        "promoter_holding": field(shareholding, "Uploaded shareholding / annual report", "fetched" if shareholding else "pending"),
        "entities": [],
        "note": "Ownership percentages are shown only when present in structured source evidence.",
    }

    business_profile = {
        "line_of_business": field(industry, _first(doc_industry_source, mca.get("provider"), "MCA / public profile"), "fetched" if industry else "pending"),
        "products_services": [],
        "customer_segments": [],
    }
    geography = {
        "registered_office": corporate_profile["registered_office"],
        "plants": [],
        "operating_states": [x for x in [_first(mca.get("registered_state"), gst.get("state"))] if x],
        "markets": [],
    }
    bank_relationship = {
        "existing_customer": field(_first(banking.get("existing_customer"), mock_borrower.get("existing_customer")), "Bank Internal / POC provider", "validated" if banking else "fetched"),
        "relationship_since": field(banking.get("relationship_since"), "Bank Internal / POC provider", "validated" if banking.get("relationship_since") else "pending"),
        "relationship_manager": field(_first(state.get("rm"), state.get("relationship_manager")), "CAM / CRM", "fetched" if _first(state.get("rm"), state.get("relationship_manager")) else "pending"),
        "account_conduct": field(banking.get("account_conduct"), "Bank Internal / POC provider", "validated" if banking.get("account_conduct") else "pending"),
        "average_utilisation_pct": field(banking.get("average_utilisation_pct"), "Bank Internal / POC provider", "validated" if banking.get("average_utilisation_pct") is not None else "pending"),
    }

    public = collect_public_information(state, external, industry or "")
    public_information = _public_summary(public)

    conflicts = []
    for label, check, a, b in [
        ("CIN", cin_check, cin, doc_cin),
        ("Company Name", company_check, name, _first(gst.get("legal_name"), pan_api.get("name"), doc_company)),
        ("PAN", pan_check, pan, doc_pan),
        ("GSTIN", gst_check, gstin, doc_gstin),
    ]:
        if check["status"] == "review_required":
            conflicts.append({"field": label, "primary": a, "comparison": b, "status": "review_required"})

    sources = []
    if mca:
        sources.append(_source_row("MCA Master Data", mca.get("provider") or "MCA / FileSure", "official_source", "Fetched from corporate master data source"))
    if pan_api:
        sources.append(_source_row("PAN Verification", pan_api.get("provider") or "PAN API", "verified" if pan_check["status"] == "verified" else "official_source"))
    if gst:
        sources.append(_source_row("GST Registration", gst.get("provider") or "GST API", "verified" if gst_check["status"] == "verified" else "official_source"))
    if udyam:
        sources.append(_source_row("Udyam Registration", udyam.get("provider") or "Udyam API", "official_source"))
    if banking:
        sources.append(_source_row("Internal Banking", banking.get("provider") or "Bank Internal", "validated"))
    for doc in documents[:12]:
        status = str(doc.get("status") or "processed").lower()
        ui_status = "verified" if status in {"confirmed", "auto_accepted"} else ("review_required" if status in {"needs_review", "low_confidence"} else "processed")
        sources.append(_source_row(doc.get("display_name") or doc.get("original_filename") or "Uploaded Document", "Uploaded Document", ui_status, doc.get("original_filename")))
    if public_information.get("mode") not in (None, "off"):
        sources.append(_source_row("Public Information Search", f"Public Search ({public_information.get('mode')})", "fetched"))

    verified = sum(1 for x in sources if x["status"] in {"verified", "matched"})
    official = sum(1 for x in sources if x["status"] == "official_source")
    validated = sum(1 for x in sources if x["status"] == "validated")
    pending = sum(1 for x in sources if x["status"] in {"review_required", "pending"}) + len(conflicts)

    profile = {
        "company_name": name,
        # Legacy shape retained for existing CAM report_builder/business-overview compatibility.
        "borrower_details": {
            "company_name": name,
            "cin": cin,
            "pan": pan,
            "gstin": gstin,
            "constitution": constitution,
            "industry": industry,
            "registered_office": registered_office,
            "year_of_incorporation": str(incorporation) if incorporation is not None else None,
            "paid_up_capital": _first(mca.get("paid_up_capital"), mca.get("paid_up_capital_cr")),
            "authorised_capital": _first(mca.get("authorized_capital"), mca.get("authorized_capital_cr")),
            "company_status": _first(mca.get("company_status"), mca.get("status")),
        },
        "corporate_profile": corporate_profile,
        "registration": registration,
        "promoters_directors": directors,
        "ownership": ownership,
        "business_profile": business_profile,
        "geography": geography,
        "bank_relationship": bank_relationship,
        "public_information": public_information,
        "source_conflicts": conflicts,
        "sources": sources,
        "verification_summary": {
            "total_sources": len(sources),
            "verified": verified,
            "official_fetched": official,
            "validated": validated,
            "pending_issues": pending,
            "message": "Borrower information compiled from internal, document, official/external and public sources. Review any highlighted conflicts before final credit use.",
        },
    }
    if include_ai:
        ai = build_ai_overview(profile)
        profile["ai_overview"] = ai.get("text")
        profile["ai_overview_source"] = ai.get("source")
        profile["llm_status"] = ai.get("llm_status")
    return profile
