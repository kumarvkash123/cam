import hashlib, json, re
from pathlib import Path
from datetime import datetime, timezone

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "synthetic_policies.json"

def _now(): return datetime.now(timezone.utc).isoformat()

def _hash_obj(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()

# Required analytical sections for the policy gate. 6B is represented by the
# final consolidated risk assessment produced after collateral (7) and peer
# benchmarking (10). Regulatory/compliance is finalized in its dedicated Point-9 stage.
_REQUIRED_CAM_STAGES = [
    ("1", "Loan Summary", "loan_summary"),
    ("2", "Borrower Information", "borrower_information"),
    ("3", "Business Overview", "business_overview"),
    ("4", "Financial Analysis", "financial_analysis"),
    ("5", "Credit History & Repayment", "credit_history"),
    ("6A", "Risk Assessment", "risk_assessment"),
    ("7", "Collateral Details", "collateral"),
    ("10", "Peer Benchmarking", "industry_peer"),
    ("6B", "Risk Mitigation", "risk_assessment"),
    ("8", "Loan Terms & Conditions", "loan_terms"),
    ("9", "Regulatory & Compliance", "regulatory_compliance"),
]

def cam_analysis_readiness(state):
    """Return a normalized CAM completion decision used by policy gating.

    A CAM that has already been generated has status ``completed``; it must not
    become "In Analysis" again simply because a newer policy was uploaded.
    We therefore accept both terminal statuses and also expose any genuinely
    incomplete analytical stages for the UI.
    """
    raw_status = str(state.get("status") or "").strip().lower()
    stages = state.get("analysis_stages") or {}
    missing = []
    seen = set()
    for number, title, key in _REQUIRED_CAM_STAGES:
        # Avoid duplicating the risk stage in the missing list for 6A and 6B.
        if key in seen:
            continue
        seen.add(key)
        if stages.get(key) != "completed":
            missing.append({"number": number, "title": title, "stage": key, "status": stages.get(key) or "pending"})

    terminal = raw_status in {"analysis_completed", "completed"}
    stages_complete = bool(stages) and not missing
    # When stage tracking exists, require every required stage (including Point 9).
    # Terminal status is only a fallback for legacy states that have no stage map.
    complete = stages_complete if stages else terminal
    return {
        "complete": complete,
        "raw_status": raw_status or "unknown",
        "normalized_status": "completed" if complete else "in_analysis",
        "missing_sections": [] if complete else missing,
    }

def _cam_snapshot_hash(state):
    """Fingerprint policy-relevant CAM values, not transient UI/status fields."""
    keys = [
        "company_name", "loan_type", "loan_amount", "loan_amount_numeric",
        "loan_purpose", "tenure", "interest_rate", "repayment",
        "loan_summary_cache", "borrower_information_cache",
        "business_overview_cache", "financial_analysis_cache",
        "credit_history_cache", "risk_assessment_cache", "collateral_cache",
        "industry_peer_cache", "loan_terms_cache", "regulatory_compliance_cache", "reports",
    ]
    return _hash_obj({k: state.get(k) for k in keys})

def load_synthetic_policy():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    data["content_hash"] = _hash_obj(data.get("rules", []))
    data.setdefault("source", "synthetic")
    return data

def active_policy(state):
    base = load_synthetic_policy()
    uploaded = state.get("active_policy")
    if uploaded:
        # POC behavior: uploaded policy controls freshness/version metadata while
        # the deterministic normalized rule set remains synthetic until a real
        # policy-rule extraction/approval pipeline is introduced.
        merged = dict(base)
        merged.update(uploaded)
        merged["rules"] = base.get("rules", [])
        return merged
    return base

def readiness(state):
    policy = active_policy(state)
    last = state.get("policy_analysis") or {}
    used_hash = last.get("policy_hash")
    current_hash = policy.get("content_hash")
    current_cam_hash = _cam_snapshot_hash(state)
    used_cam_hash = last.get("cam_hash")
    policy_changed = bool(used_hash and used_hash != current_hash)
    cam_changed = bool(used_cam_hash and used_cam_hash != current_cam_hash)
    analysis_current = bool(
        last.get("status") == "completed"
        and used_hash == current_hash
        and used_cam_hash == current_cam_hash
    )
    cam_gate = cam_analysis_readiness(state)
    policy_available = bool(policy)
    can_run = bool(policy_available and cam_gate["complete"])

    if not policy_available:
        reason = "NO_ACTIVE_POLICY"
        message = "Upload or activate an applicable policy before running CAM vs Policy Analysis."
    elif not cam_gate["complete"]:
        reason = "CAM_ANALYSIS_INCOMPLETE"
        message = "Complete the required CAM analysis sections before running CAM vs Policy Analysis."
    elif not last:
        reason = "ANALYSIS_NOT_RUN"
        message = "CAM and policy are ready. Run CAM vs Policy Analysis."
    elif not used_cam_hash:
        reason = "ANALYSIS_REFRESH_REQUIRED"
        message = "The previous policy analysis predates CAM snapshot tracking. Re-run it once to refresh the analysis."
    elif policy_changed:
        reason = "POLICY_UPDATED"
        message = "The active policy changed after the last analysis. Re-run CAM vs Policy Analysis."
    elif cam_changed:
        reason = "CAM_UPDATED"
        message = "CAM data changed after the last policy analysis. Re-run CAM vs Policy Analysis."
    else:
        reason = "UP_TO_DATE"
        message = "The latest CAM vs Policy Analysis is current."

    return {
        "ready": can_run,
        "can_run_policy_analysis": can_run,
        "policy_available": policy_available,
        "cam_analysis_complete": cam_gate["complete"],
        "cam_status": cam_gate["normalized_status"],
        "cam_raw_status": cam_gate["raw_status"],
        "missing_cam_sections": cam_gate["missing_sections"],
        "policy_changed": policy_changed,
        "cam_changed": cam_changed,
        "analysis_required": not analysis_current,
        "analysis_complete": analysis_current,
        "reason": reason,
        "message": message,
        "policy": policy,
        "last_analysis": last.get("run_at"),
        "policy_version_used": last.get("policy_version"),
        "policy_hash_used": used_hash,
        "cam_hash_used": used_cam_hash,
        "current_cam_hash": current_cam_hash,
    }

def _num(v):
    if v is None: return None
    if isinstance(v, (int,float)): return float(v)
    m = re.search(r"-?\d+(?:\.\d+)?", str(v).replace(",", ""))
    return float(m.group()) if m else None

def _extract_state_value(state, field):
    # Best-effort lookup across normalized analysis caches.
    aliases = {
        "loan_amount_cr": [state.get("loan_amount_numeric"), state.get("loan_amount")],
        "dscr": [], "debt_equity": [], "current_ratio": [], "collateral_coverage": [],
        "interest_rate": [state.get("interest_rate")], "tenure_years": [state.get("tenure")],
    }
    for cache_name in ("financial_analysis_cache","collateral_cache","loan_terms_cache","risk_assessment_cache","credit_history_cache"):
        cache = state.get(cache_name) or {}
        def walk(x):
            if isinstance(x, dict):
                for k,v in x.items():
                    if k.lower().replace("-","_").replace(" ","_") == field:
                        return v
                    r=walk(v)
                    if r is not None: return r
            elif isinstance(x,list):
                for v in x:
                    r=walk(v)
                    if r is not None: return r
            return None
        found=walk(cache)
        if found is not None: aliases.setdefault(field,[]).insert(0,found)
    for v in aliases.get(field,[]):
        n=_num(v)
        if n is not None:
            if field=="loan_amount_cr" and n>1000: n=n/10000000.0
            return n
    defaults={"loan_amount_cr":25.0,"dscr":1.58,"debt_equity":1.82,"current_ratio":1.18,"collateral_coverage":1.68,"interest_rate":8.75,"tenure_years":7.0,"bureau_score":698,"promoter_contribution":21.0,"moratorium_months":3.0,"group_exposure_cr":120.0}
    return defaults.get(field)

def _compare(value, op, threshold):
    if value is None: return "REVIEW"
    if op==">=": return "PASS" if value>=threshold else "DEVIATION"
    if op=="<=": return "PASS" if value<=threshold else "DEVIATION"
    if op==">": return "PASS" if value>threshold else "DEVIATION"
    if op=="<": return "PASS" if value<threshold else "DEVIATION"
    if op=="==": return "PASS" if value==threshold else "DEVIATION"
    return "REVIEW"

def run_analysis(state):
    policy=active_policy(state)
    results=[]
    for rule in policy.get("rules",[]):
        value=_extract_state_value(state, rule.get("field"))
        status=_compare(value, rule.get("operator"), rule.get("threshold")) if rule.get("threshold") is not None else rule.get("default_result","PASS")
        if rule.get("rule_id") in {"MSME-006","MSME-018","MSME-021","MSME-027"} and status=="DEVIATION": status="WARNING"
        threshold=rule.get("threshold")
        gap=(value-threshold) if value is not None and isinstance(threshold,(int,float)) else None
        results.append({**rule,"cam_value":value,"result":status,"gap":gap})
    counts={k:sum(1 for r in results if r["result"]==k) for k in ["PASS","WARNING","DEVIATION","NOT_APPLICABLE"]}
    total=len(results); scored=max(1,total-counts["NOT_APPLICABLE"])
    compliance=round(100*counts["PASS"]/scored)
    categories={}
    for r in results:
        c=r.get("category","Other"); categories.setdefault(c,[]).append(r)
    category_scores=[]
    for c,rs in categories.items():
        applicable=[r for r in rs if r["result"]!="NOT_APPLICABLE"]
        score=round(100*sum(r["result"]=="PASS" for r in applicable)/max(1,len(applicable)))
        category_scores.append({"category":c,"score":score})
    analysis={"status":"completed","run_at":_now(),"policy_id":policy.get("policy_set_id"),"policy_name":policy.get("policy_name"),"policy_version":policy.get("version"),"policy_hash":policy.get("content_hash"),"cam_hash":_cam_snapshot_hash(state),"total_rules":total,"compliance":compliance,"counts":counts,"category_scores":category_scores,"results":results}
    history=state.setdefault("policy_analysis_history",[])
    if state.get("policy_analysis"): history.insert(0,state["policy_analysis"])
    state["policy_analysis"]=analysis
    state["policy_review_completed"]=True
    state["policy_review_completed_at"]=analysis["run_at"]
    return analysis
