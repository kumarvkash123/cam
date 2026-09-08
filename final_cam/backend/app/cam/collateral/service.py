"""Collateral Details (CAM Point 7).

Extracts and normalizes collateral/security evidence, performs deterministic
valuation/coverage/ownership/charge/document checks, and uses the LLM only to
phrase a bounded commentary from verified structured facts.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.cam.llm_gateway import chat as llm_chat, LLMGatewayError
from app.cam.loan_summary_service.external_data_service import collect_external_data

MISSING = (None, "", "—", "N/A", "Not available")


def _norm(s: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s or "").lower()).strip("_")


def _num(v: Any) -> Optional[float]:
    if v in MISSING: return None
    if isinstance(v, (int, float)): return float(v)
    s = str(v).replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def _cr(v: Any) -> Optional[float]:
    n = _num(v)
    if n is None: return None
    s = str(v).lower()
    if "crore" in s or re.search(r"\bcr\b", s): return round(n, 4)
    if "lakh" in s or "lac" in s: return round(n / 100, 4)
    # Raw document/API numbers are normally rupees when large.
    if abs(n) >= 100000: return round(n / 10000000, 4)
    return round(n, 4)


def _date(v: Any) -> Optional[datetime]:
    if v in MISSING: return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d %b %Y", "%d.%m.%Y"):
        try: return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError: pass
    return None


def _field_map(documents: List[Dict[str, Any]]) -> Dict[str, List[Tuple[Any, Dict[str, Any]]]]:
    out: Dict[str, List[Tuple[Any, Dict[str, Any]]]] = {}
    for d in documents:
        for k, v in (d.get("extracted_fields") or {}).items():
            if v in MISSING: continue
            out.setdefault(_norm(k), []).append((v, d))
    return out


def _find(fmap, *names):
    for n in names:
        rows = fmap.get(_norm(n)) or []
        if rows: return rows[0][0], rows[0][1]
    return None, None


def _doc_kind(d: Dict[str, Any]) -> str:
    s = " ".join(str(d.get(x) or "") for x in ("doc_type", "display_name", "original_filename")).lower()
    if "valuation" in s or "valuer" in s: return "Valuation Report"
    if any(x in s for x in ("sale deed", "title deed", "conveyance", "lease deed", "property deed")): return "Sale Deed / Title Document"
    if any(x in s for x in ("legal search", "title search", "legal opinion", "encumbrance")): return "Legal Search Report"
    if "insurance" in s: return "Insurance Policy"
    if any(x in s for x in ("charge", "mortgage", "roc")): return "Charge Registration Proof"
    if any(x in s for x in ("stock statement", "inventory")): return "Stock Statement"
    if any(x in s for x in ("fixed deposit", "fd receipt")): return "Fixed Deposit"
    return ""


def _document_checks(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    expected = ["Valuation Report", "Sale Deed / Title Document", "Legal Search Report", "Insurance Policy", "Charge Registration Proof"]
    seen = {}
    for d in documents:
        k = _doc_kind(d)
        if k and k not in seen: seen[k] = d
    rows = []
    for label in expected:
        d = seen.get(label)
        rows.append({
            "document": label,
            "status": "Available" if d else "Not available",
            "remarks": (d.get("original_filename") if d else "Upload / verify if applicable"),
            "document_id": d.get("document_id") if d else None,
        })
    return rows


def _security_type(text: str) -> Tuple[str, str]:
    s = text.lower()
    if any(x in s for x in ("land", "building", "property", "plot", "factory")): return "Immovable Property", "Collateral"
    if any(x in s for x in ("plant", "machinery", "equipment", "vehicle")): return "Movable Asset", "Collateral"
    if any(x in s for x in ("stock", "inventory", "receivable", "book debt")): return "Current Assets", "Primary"
    if any(x in s for x in ("fixed deposit", " fd ", "deposit")): return "Financial Security", "Collateral"
    if "guarantee" in s: return "Guarantee", "Additional"
    return "Other Security", "Collateral"


def _securities(state: Dict[str, Any], documents: List[Dict[str, Any]], fmap) -> List[Dict[str, Any]]:
    # Prefer structured collateral/security objects if supplied by LOS/manual input.
    raw = state.get("collateral") or state.get("collaterals") or state.get("securities") or []
    if isinstance(raw, dict): raw = raw.get("items") or raw.get("securities") or [raw]
    rows: List[Dict[str, Any]] = []
    if isinstance(raw, list):
        for i, x in enumerate(raw):
            if not isinstance(x, dict): continue
            desc = x.get("description") or x.get("security") or x.get("asset") or f"Security {i+1}"
            typ, category = _security_type(str(desc) + " " + str(x.get("type") or ""))
            market = _cr(x.get("market_value") or x.get("valuation_amount") or x.get("value"))
            real = _cr(x.get("realizable_value") or x.get("realisable_value"))
            eligible = _cr(x.get("eligible_value"))
            if eligible is None: eligible = real if real is not None else market
            rows.append({"id":f"COL-{i+1:03d}","security":desc,"type":x.get("type") or typ,"category":x.get("category") or category,
                         "owner":x.get("owner") or x.get("owner_name") or "Not available","market_value_cr":market,
                         "realizable_value_cr":real,"distress_value_cr":_cr(x.get("distress_value") or x.get("forced_sale_value")),
                         "eligible_value_cr":eligible,"charge":x.get("charge") or x.get("charge_type") or "Not verified",
                         "charge_status":x.get("charge_status") or "Not verified","valuation_date":x.get("valuation_date"),
                         "valuer":x.get("valuer") or x.get("valuer_name") or "Not available", "source":"Internal / proposal data"})
    if rows: return rows

    # Document-derived single/multiple security cues. We deliberately do not invent assets.
    desc, ddesc = _find(fmap, "security_description", "collateral_description", "asset_description", "property_description", "security_asset")
    market, dm = _find(fmap, "market_value", "market_value_of_property", "valuation_amount", "property_value", "fair_market_value")
    real, dr = _find(fmap, "realizable_value", "realisable_value", "realisable_market_value")
    distress, dd = _find(fmap, "distress_value", "forced_sale_value", "forced_sale_realizable_value")
    owner, do = _find(fmap, "owner_name", "property_owner", "ownership", "name_of_owner")
    charge, dc = _find(fmap, "charge_type", "nature_of_charge", "mortgage_type", "charge_status")
    vdate, dv = _find(fmap, "valuation_date", "date_of_valuation", "valuation_report_date")
    valuer, dval = _find(fmap, "valuer", "valuer_name", "name_of_valuer")
    if any(v not in (None, "") for v in (desc, market, real, distress, owner, charge)):
        description = str(desc or "Collateral / security extracted from uploaded evidence")
        typ, category = _security_type(description)
        mcr, rcr = _cr(market), _cr(real)
        rows.append({"id":"COL-001","security":description,"type":typ,"category":category,"owner":owner or "Not available",
                     "market_value_cr":mcr,"realizable_value_cr":rcr,"distress_value_cr":_cr(distress),
                     "eligible_value_cr":rcr if rcr is not None else mcr,"charge":charge or "Not verified","charge_status":"Not verified",
                     "valuation_date":vdate,"valuer":valuer or "Not available",
                     "source":(dm or dr or ddesc or do or dc or dv or dval or {}).get("original_filename","Uploaded documents")})
    return rows


def _mca_charge_findings(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    external = collect_external_data(state)
    mca = ((external.get("api") or {}).get("mca_response") or {})
    findings=[]
    def walk(obj, path=""):
        if isinstance(obj, dict):
            # Preserve structured charge records when present.
            keys = {_norm(k):k for k in obj}
            if any("charge" in k for k in keys):
                text = " | ".join(f"{k}: {v}" for k,v in obj.items() if not isinstance(v,(dict,list)) and "charge" in _norm(k))
                if text: findings.append({"source":"MCA","detail":text,"status":"Review"})
            for k,v in obj.items(): walk(v, path+"/"+str(k))
        elif isinstance(obj, list):
            for x in obj: walk(x,path)
    walk(mca)
    # Deduplicate and bound UI payload.
    seen=set(); out=[]
    for x in findings:
        if x["detail"] in seen: continue
        seen.add(x["detail"]); out.append(x)
    return out[:8]


def _coverage(state: Dict[str, Any], securities: List[Dict[str, Any]]) -> Dict[str, Any]:
    market = round(sum(x.get("market_value_cr") or 0 for x in securities),2) if securities else None
    eligible = round(sum(x.get("eligible_value_cr") or 0 for x in securities),2) if securities else None
    exposure = _cr(state.get("loan_amount_numeric") or state.get("loan_amount") or state.get("requested_amount"))
    # POC default only; clearly marked configurable, not asserted as BOB policy.
    threshold = _num(state.get("collateral_coverage_threshold")) or 1.50
    ratio = round(eligible / exposure, 2) if eligible is not None and exposure not in (None,0) else None
    status = "Not assessed" if ratio is None else "Adequate" if ratio >= threshold else "Deviation"
    return {"market_value_cr":market,"eligible_value_cr":eligible,"proposed_exposure_cr":exposure,
            "coverage_ratio":ratio,"policy_threshold":threshold,"status":status,
            "threshold_source":"POC configurable threshold; replace with product/policy rule"}


def _valuation_rows(securities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now=datetime.now(timezone.utc); rows=[]
    for s in securities:
        dt=_date(s.get("valuation_date")); age=None
        if dt: age=max(0, round((now-dt).days/30.44))
        status="Not available" if not dt else "Current" if age <= 12 else "Revaluation Required"
        rows.append({"security":s["security"],"valuer":s.get("valuer") or "Not available","valuation_date":s.get("valuation_date") or "Not available",
                     "market_value_cr":s.get("market_value_cr"),"realizable_value_cr":s.get("realizable_value_cr"),"distress_value_cr":s.get("distress_value_cr"),
                     "age_months":age,"status":status})
    return rows


def _checks(state, securities, mca_findings, fmap):
    borrower = str(state.get("company_name") or state.get("company") or "").strip().lower()
    owner = next((str(s.get("owner") or "") for s in securities if s.get("owner") not in MISSING), "")
    owner_status = "Not verified" if not borrower or not owner else "Matched" if borrower in owner.lower() or owner.lower() in borrower else "Review"
    title_owner, _ = _find(fmap,"title_owner","registered_owner","property_owner")
    val_owner, _ = _find(fmap,"valuation_owner","owner_name","name_of_owner")
    title_match = "Not verified" if not title_owner or not val_owner else "Matched" if _norm(title_owner)==_norm(val_owner) else "Review"
    enc, _ = _find(fmap,"encumbrance","encumbrance_status","litigation","title_status")
    ins_exp, _ = _find(fmap,"insurance_expiry","policy_expiry_date","insurance_expiry_date")
    exp_dt=_date(ins_exp); insurance="Not verified"
    if exp_dt:
        days=(exp_dt-datetime.now(timezone.utc)).days
        insurance="Expired" if days < 0 else "Expiring Soon" if days <= 60 else "Current"
    return [
        {"check":"Owner vs Borrower","status":owner_status,"detail":owner or "Owner not available"},
        {"check":"Title vs Valuation","status":title_match,"detail":"Cross-document ownership comparison"},
        {"check":"MCA Charge Search","status":"Review" if mca_findings else "Not verified","detail":mca_findings[0]["detail"] if mca_findings else "No structured charge evidence available"},
        {"check":"Encumbrance / Litigation","status":"Review" if enc else "Not verified","detail":str(enc or "No structured legal-search result available")},
        {"check":"Charge Registration","status":"Review" if any(str(s.get("charge_status","")).lower() in ("pending","not verified") for s in securities) else "Matched","detail":"Based on available security/charge evidence"},
        {"check":"Insurance Coverage","status":insurance,"detail":str(ins_exp or "Insurance expiry not available")},
    ]


def _observations(coverage, valuations, checks, securities, docs):
    out=[]
    if coverage["coverage_ratio"] is not None:
        out.append({"level":"good" if coverage["status"]=="Adequate" else "risk","text":f"Security coverage is {coverage['coverage_ratio']:.2f}x against configured threshold {coverage['policy_threshold']:.2f}x."})
    else: out.append({"level":"info","text":"Security coverage cannot be calculated until eligible value and proposed exposure are available."})
    for v in valuations:
        if v["status"]=="Revaluation Required": out.append({"level":"watch","text":f"Valuation for {v['security']} is {v['age_months']} months old; fresh valuation should be reviewed."})
    for c in checks:
        if c["status"] in ("Review","Expired","Expiring Soon"):
            out.append({"level":"watch" if c["status"]!="Expired" else "risk","text":f"{c['check']}: {c['detail']}"})
    missing=[x["document"] for x in docs if x["status"]!="Available"]
    if missing: out.append({"level":"info","text":"Document evidence not available for: "+", ".join(missing[:3])+("…" if len(missing)>3 else "")+"."})
    if securities and all(str(s.get("owner","")).lower() not in ("","not available") for s in securities): out.append({"level":"good","text":"Ownership details are available for all captured securities; cross-verification status is shown separately."})
    return out[:10]


def _commentary(company, coverage, securities, observations, include_ai):
    base = (f"Collateral analysis for {company} is based only on available uploaded and structured evidence. "
            + (f"Eligible security is ₹{coverage['eligible_value_cr']:.2f} Cr against proposed exposure of ₹{coverage['proposed_exposure_cr']:.2f} Cr, giving {coverage['coverage_ratio']:.2f}x coverage. " if coverage.get("coverage_ratio") is not None else "Security coverage is not yet calculable from available evidence. ")
            + "Material charge, valuation-age, ownership, legal and insurance items should be verified before relying on collateral for sanction or disbursement.")
    if not include_ai: return {"source":"deterministic","text":base,"error":""}
    try:
        text=llm_chat([
            {"role":"system","content":"You are a bank CAM analyst. Draft one concise Collateral Details paragraph using ONLY supplied structured facts. Do not invent title clearance, charge priority, insurance, ownership, value, policy compliance or legal conclusions. Distinguish not verified from clear. Max 140 words."},
            {"role":"user","content":json.dumps({"company":company,"coverage":coverage,"securities":securities[:6],"observations":observations[:8]},ensure_ascii=False)}
        ],temperature=0.1)
        return {"source":"ai_generated","text":str(text).strip(),"error":""}
    except (LLMGatewayError,TypeError,ValueError) as exc:
        return {"source":"deterministic","text":base,"error":str(exc)}


def build_collateral_analysis(state: Dict[str, Any], documents: List[Dict[str, Any]], include_ai: bool=True) -> Dict[str, Any]:
    fmap=_field_map(documents)
    securities=_securities(state,documents,fmap)
    coverage=_coverage(state,securities)
    valuations=_valuation_rows(securities)
    mca_findings=_mca_charge_findings(state)
    checks=_checks(state,securities,mca_findings,fmap)
    docs=_document_checks(documents)
    obs=_observations(coverage,valuations,checks,securities,docs)
    company=state.get("company_name") or state.get("company") or "Borrower"
    commentary=_commentary(company,coverage,securities,obs,include_ai)
    sources=[]
    for d in documents:
        if _doc_kind(d): sources.append({"type":"document","name":d.get("original_filename"),"document_type":_doc_kind(d),"document_id":d.get("document_id")})
    if mca_findings: sources.append({"type":"external","name":"MCA charge data","document_type":"MCA","document_id":None})
    return {
        "point":7,"title":"Collateral Details (if applicable)","company_name":company,"cam_id":state.get("cam_id"),
        "summary":{"security_count":len(securities),"primary_count":sum(1 for s in securities if s.get("category")=="Primary"),"collateral_count":sum(1 for s in securities if s.get("category")=="Collateral"),**coverage},
        "securities":securities,"valuations":valuations,"coverage":coverage,"validation_checks":checks,"document_checks":docs,
        "mca_charge_findings":mca_findings,"observations":obs,"commentary":commentary,"sources":sources[:12],
        "methodology":"Collateral facts are extracted/normalized from available security, valuation, title/legal, insurance, internal and MCA evidence. Coverage, valuation ageing and rule statuses are deterministic. AI is used only to phrase commentary. Missing evidence remains Not verified / Not available.",
        "decision_notice":"Collateral analysis is decision support only. Title, enforceability, valuation acceptability, charge priority and policy compliance require bank/legal/valuer verification."
    }
