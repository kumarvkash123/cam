from flask import jsonify, request, send_file
from app.cam.blueprint import cam_bp
from app.cam.core import *
from app.cam.llm_gateway import chat as groq_chat, LLMGatewayError
from app.cam.loan_summary import build_loan_summary
from app.cam.policy_engine import active_policy, readiness as policy_readiness, run_analysis
import hashlib, json

@cam_bp.route("/api/cam/policies/<session_id>", methods=["POST"])
def cam_policies(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    files = [f for f in request.files.getlist("file") if f and f.filename]
    if not files:
        return jsonify({"error": "No policy files selected"}), 400
    results = []
    for f in files:
        name = secure_filename(f.filename)
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in POLICY_EXTENSIONS:
            results.append({"filename": name, "status": "rejected", "error": "Unsupported policy file type"})
            continue
        try:
            src = extract_policy_source(f, state["application_id"])
            state["policy_sources"].append(src)
            results.append({"filename": src["filename"], "category": src["category"], "status": "indexed", "page_count": src["page_count"]})
        except Exception as exc:
            results.append({"filename": name, "status": "failed", "error": str(exc)})
    if state.get("policy_sources"):
        joined = "\n".join(str(x.get("text") or "") for x in state.get("policy_sources", []))
        digest = hashlib.sha256(joined.encode("utf-8", errors="ignore")).hexdigest()
        state["active_policy"] = {
            "policy_set_id": "UPLOADED-POLICY",
            "policy_name": "Uploaded Bank Policy Set",
            "loan_type": state.get("loan_type") or "Applicable facility",
            "version": f"UPL-{now_iso()[:10]}",
            "effective_date": now_iso()[:10],
            "updated_at": now_iso(),
            "status": "ACTIVE",
            "source": "uploaded",
            "content_hash": digest,
            "total_rules": len(active_policy(state).get("rules", [])),
        }
    state["policy_review_completed"] = False
    state["policy_review_completed_at"] = None
    state.pop("policy_analysis", None)
    save_cam(state)
    return jsonify({"status": "completed", "results": results, "message": "Policy documents indexed. You can now chat with the policy documents."})
@cam_bp.route("/api/cam/policies/<session_id>", methods=["GET"])
def cam_policy_list(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    return jsonify({"documents": [
        {"filename": s.get("filename"), "category": s.get("category"), "status": s.get("status"), "page_count": s.get("page_count")} for s in state.get("policy_sources", [])
    ]})
@cam_bp.route("/api/cam/policy-chat/<session_id>", methods=["POST"])
def cam_policy_chat(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    sources = state.get("policy_sources") or []
    if not sources:
        policy = active_policy(state)
        lines = []
        for r in policy.get("rules", []):
            threshold = f"{r.get('operator','')} {r.get('threshold','')} {r.get('unit','')}".strip()
            lines.append(f"{r.get('rule_id')}: {r.get('title')} | {threshold} | {r.get('source_ref','Synthetic policy')}")
        text = "\n".join(lines)
        sources = [{
            "filename": "synthetic_msmE_credit_policy_2026.txt",
            "category": "Synthetic Policy",
            "status": "indexed",
            "text": text,
            "pages": [{"page_no": 1, "text": text, "words": []}],
            "page_count": 1,
        }]
    data = request.get_json(silent=True) or request.form
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    result = answer_question(message, sources, state.get("policy_chat", []))
    state["policy_chat"].append({"role": "user", "content": message})
    state["policy_chat"].append({"role": "assistant", "content": result["answer"]})
    save_cam(state)
    return jsonify(result)


@cam_bp.route("/api/cam/policy-review/<session_id>", methods=["POST"])
def cam_policy_review_complete(session_id):
    """Record the human policy-review gate before final CAM generation."""
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    if state.get("status") not in ("analysis_completed", "completed"):
        return jsonify({"error": "Complete CAM analysis before policy review"}), 400
    if not state.get("policy_sources"):
        return jsonify({"error": "Upload and index at least one applicable policy document first"}), 400

    state["policy_review_completed"] = True
    state["policy_review_completed_at"] = now_iso()
    save_cam(state)
    return jsonify({
        "status": "completed",
        "policy_review_completed": True,
        "completed_at": state["policy_review_completed_at"],
        "message": "CAM vs Policy review recorded. Final CAM review is now available.",
    })


@cam_bp.route("/api/cam/policy-active/<session_id>", methods=["GET"])
def cam_policy_active(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    policy = active_policy(state)
    payload = dict(policy)
    payload["total_rules"] = len(policy.get("rules", []))
    payload.pop("rules", None)
    return jsonify(payload)

@cam_bp.route("/api/cam/policy-readiness/<session_id>", methods=["GET"])
def cam_policy_readiness(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    r = policy_readiness(state)
    policy = dict(r.get("policy") or {})
    policy["total_rules"] = len(policy.get("rules", []))
    policy.pop("rules", None)
    r["policy"] = policy
    return jsonify(r)

@cam_bp.route("/api/cam/policy-analysis/<session_id>", methods=["GET", "POST"])
def cam_policy_analysis(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    if request.method == "GET":
        analysis = state.get("policy_analysis")
        if not analysis:
            return jsonify({"status": "not_run", "analysis": None, "readiness": policy_readiness(state)})
        return jsonify({"status": analysis.get("status"), "analysis": analysis, "readiness": policy_readiness(state)})
    gate = policy_readiness(state)
    if not gate.get("policy_available"):
        return jsonify({"error": "No active policy is available", "readiness": gate}), 400
    if not gate.get("cam_analysis_complete"):
        return jsonify({
            "error": "Complete the required CAM analysis sections before running CAM vs Policy Analysis",
            "readiness": gate,
            "missing_cam_sections": gate.get("missing_cam_sections", []),
        }), 400
    analysis = run_analysis(state)
    save_cam(state)
    return jsonify({"status": "completed", "analysis": analysis, "readiness": policy_readiness(state)})

@cam_bp.route("/api/cam/policy-history/<session_id>", methods=["GET"])
def cam_policy_history(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    current = state.get("policy_analysis")
    history = list(state.get("policy_analysis_history") or [])
    if current:
        history.insert(0, current)
    compact=[]
    for x in history[:10]:
        compact.append({k:x.get(k) for k in ["policy_version","run_at","compliance","counts","status"]})
    return jsonify({"history": compact})
