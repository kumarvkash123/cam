from flask import jsonify, request, send_file
from app.cam.blueprint import cam_bp
from app.cam.core import *
from app.cam.llm_gateway import chat as groq_chat, LLMGatewayError
from app.cam.loan_summary import build_loan_summary
from app.cam.readiness import build_readiness
from app.cam.borrower_info import build_borrower_profile
from app.cam.business_overview import build_business_overview
from app.cam.financial_analysis import build_financial_analysis
from app.cam.credit_history import build_credit_history
from app.cam.risk_assessment import build_risk_assessment
from app.cam.collateral import build_collateral_analysis
from app.cam.loan_terms import build_loan_terms
from app.cam.industry_peer import build_industry_peer_analysis
from app.cam.regulatory_compliance import build_regulatory_compliance


@cam_bp.route("/api/cam/readiness/<session_id>", methods=["GET"])
def cam_readiness(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    db, row = get_db_application(session_id)
    if not row:
        if db: db.close()
        return jsonify({"error": "Application not found"}), 404
    documents = [document_payload(d) for d in row.documents]
    db.close()
    payload = build_readiness(state, documents)
    payload["cam_id"] = state.get("cam_id")
    payload["company_name"] = state.get("company_name") or state.get("company")
    return jsonify(payload)

@cam_bp.route("/api/cam/analyze/<session_id>", methods=["POST"])
def cam_analyze(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    # CAM analysis must not be blocked by conversational fields that have not yet
    # been captured. These fields can be completed later through the CAM Assistant
    # and are shown as "Not available" until then. In particular, do not return
    # the old "Loan type is required" validation error here.
    missing_fields = []
    if not str(state.get("loan_type", "")).strip():
        missing_fields.append("Loan Type")
    if state.get("loan_amount_numeric") is None:
        missing_fields.append("Requested Amount")
    for key, label in (("loan_purpose", "Loan Purpose"), ("tenure", "Tenure"),
                       ("interest_rate", "Interest Rate"), ("repayment", "Repayment Structure")):
        if not str(state.get(key, "")).strip():
            missing_fields.append(label)
    state["analysis_missing_inputs"] = missing_fields
    if missing_fields:
        state["current_step"] = "Analysis started; some proposal fields are pending"

    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return jsonify({"error": "Application not found"}), 404
    document_count = len(row.documents)
    db.close()
    if document_count == 0:
        return jsonify({"error": "Upload at least one supporting document before starting CAM analysis"}), 400

    state["conversation_state"] = "analysis"
    state["status"] = "queued"
    state["error"] = ""
    save_cam(state)
    threading.Thread(target=process_analysis, args=(session_id,), daemon=True).start()
    return jsonify({"status": "queued", "message": "CAM analysis started", "cam_id": state["cam_id"]})
@cam_bp.route("/api/cam/reports/<session_id>", methods=["GET"])
def cam_reports(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    if state.get("status") not in ("analysis_completed", "completed"):
        return jsonify({"error": "CAM analysis is not completed yet"}), 400
    if not state.get("reports"):
        db, row = get_db_application(session_id)
        if not row:
            if db:
                db.close()
            return jsonify({"error": "Application not found"}), 404
        documents = [document_payload(d, include_text=True) for d in row.documents]
        db.close()
        state["reports"] = build_cam_reports(state, documents)
        save_cam(state)
    return jsonify({"cam_id": state["cam_id"], "reports": state["reports"]})
@cam_bp.route("/api/cam/status/<session_id>", methods=["GET"])
def cam_status(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    db, row = get_db_application(session_id)
    docs = []
    if row:
        docs = [document_payload(d) for d in row.documents]
    if db:
        db.close()
    payload = dict(state)
    payload["documents"] = docs
    payload.pop("docx_path", None)
    payload.pop("pdf_path", None)
    return jsonify(payload)

@cam_bp.route("/api/cam/borrower-information/<session_id>", methods=["GET"])
def cam_borrower_information(session_id):
    """Step-6 Borrower Information API with source provenance, deterministic verification and optional Groq overview."""
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    force = str(request.args.get("refresh", "")).lower() in ("1", "true", "yes")
    if state.get("borrower_information_cache") and not force:
        return jsonify(state["borrower_information_cache"])
    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return jsonify({"error": "Application not found"}), 404
    documents = [document_payload(d, include_text=True) for d in row.documents]
    db.close()
    payload = build_borrower_profile(state, documents, include_ai=True)
    payload["cam_id"] = state.get("cam_id")
    state["borrower_information_cache"] = payload
    state["borrower_information_ready"] = True
    save_cam(state)
    return jsonify(payload)


@cam_bp.route("/api/cam/business-overview/<session_id>", methods=["GET"])
def cam_business_overview(session_id):
    """Step-7 Business Overview API built from normalized documents, borrower profile, external/public data and Groq synthesis."""
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    force = str(request.args.get("refresh", "")).lower() in ("1", "true", "yes")
    if state.get("business_overview_cache") and not force:
        return jsonify(state["business_overview_cache"])
    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return jsonify({"error": "Application not found"}), 404
    documents = [document_payload(d, include_text=True) for d in row.documents]
    db.close()
    payload = build_business_overview(state, documents, include_ai=True)
    payload["cam_id"] = state.get("cam_id")
    state["business_overview_cache"] = payload
    state["business_overview_ready"] = True
    state["business_overview_error"] = ""
    save_cam(state)
    return jsonify(payload)



@cam_bp.route("/api/cam/financial-analysis/<session_id>", methods=["GET"])
def cam_financial_analysis(session_id):
    """Point-4 Financial Analysis API: deterministic ratios/trends/stress plus bounded AI commentary."""
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    force = str(request.args.get("refresh", "")).lower() in ("1", "true", "yes")
    if state.get("financial_analysis_cache") and not force:
        return jsonify(state["financial_analysis_cache"])
    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return jsonify({"error": "Application not found"}), 404
    documents = [document_payload(d, include_text=True) for d in row.documents]
    db.close()
    payload = build_financial_analysis(state, documents, include_ai=True)
    state["financial_analysis_cache"] = payload
    state["financial_analysis_ready"] = True
    save_cam(state)
    return jsonify(payload)

@cam_bp.route("/api/cam/credit-history/<session_id>", methods=["GET"])
def cam_credit_history(session_id):
    """Point-5 Credit History & Repayment Track Record API."""
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    force = str(request.args.get("refresh", "")).lower() in ("1", "true", "yes")
    if state.get("credit_history_cache") and not force:
        return jsonify(state["credit_history_cache"])
    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return jsonify({"error": "Application not found"}), 404
    documents = [document_payload(d, include_text=True) for d in row.documents]
    db.close()
    payload = build_credit_history(state, documents, include_ai=True)
    state["credit_history_cache"] = payload
    state["credit_history_ready"] = True
    state["credit_history_error"] = ""
    save_cam(state)
    return jsonify(payload)

@cam_bp.route("/api/cam/risk-assessment/<session_id>", methods=["GET"])
def cam_risk_assessment(session_id):
    """Point-6 Risk Assessment & Mitigation API.

    Reuses cached Point-4/5 outputs; when either cache is missing it builds that
    upstream module first from the same current evidence, then consolidates risk.
    """
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    force = str(request.args.get("refresh", "")).lower() in ("1", "true", "yes")
    if state.get("risk_assessment_cache") and not force:
        return jsonify(state["risk_assessment_cache"])
    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return jsonify({"error": "Application not found"}), 404
    documents = [document_payload(d, include_text=True) for d in row.documents]
    db.close()

    # Point 6 consumes the normalized outputs of Points 4 and 5. Build only
    # missing/explicitly refreshed dependencies; do not send raw documents to AI.
    if force or not state.get("financial_analysis_cache"):
        state["financial_analysis_cache"] = build_financial_analysis(state, documents, include_ai=False)
        state["financial_analysis_ready"] = True
    if force or not state.get("credit_history_cache"):
        state["credit_history_cache"] = build_credit_history(state, documents, include_ai=False)
        state["credit_history_ready"] = True

    payload = build_risk_assessment(state, documents, include_ai=True)
    state["risk_assessment_cache"] = payload
    state["risk_assessment_ready"] = True
    state["risk_assessment_error"] = ""
    save_cam(state)
    return jsonify(payload)



@cam_bp.route("/api/cam/collateral/<session_id>", methods=["GET"])
def cam_collateral(session_id):
    """Point-7 Collateral Details API: source-backed security, valuation, charge and coverage analysis."""
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    force = str(request.args.get("refresh", "")).lower() in ("1", "true", "yes")
    if state.get("collateral_cache") and not force:
        return jsonify(state["collateral_cache"])
    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return jsonify({"error": "Application not found"}), 404
    documents = [document_payload(d, include_text=True) for d in row.documents]
    db.close()
    payload = build_collateral_analysis(state, documents, include_ai=True)
    state["collateral_cache"] = payload
    state["collateral_ready"] = True
    state["collateral_error"] = ""
    # Collateral changes can affect Point 6; invalidate its cached consolidated view.
    state.pop("risk_assessment_cache", None)
    save_cam(state)
    return jsonify(payload)



@cam_bp.route("/api/cam/industry-peer/<session_id>", methods=["GET"])
def cam_industry_peer(session_id):
    """Point-10 Industry / Market / Peer Analysis API.

    This section is computed after Point 7 in the analytical dependency chain.
    It reuses cached Point 3/4 outputs and configured external/public evidence;
    unavailable peer metrics are never estimated.
    """
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    force = str(request.args.get("refresh", "")).lower() in ("1", "true", "yes")
    if state.get("industry_peer_cache") and not force:
        return jsonify(state["industry_peer_cache"])
    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return jsonify({"error": "Application not found"}), 404
    documents = [document_payload(d, include_text=True) for d in row.documents]
    db.close()

    if force or not state.get("business_overview_cache"):
        state["business_overview_cache"] = build_business_overview(state, documents, include_ai=False)
        state["business_overview_ready"] = True
    if force or not state.get("financial_analysis_cache"):
        state["financial_analysis_cache"] = build_financial_analysis(state, documents, include_ai=False)
        state["financial_analysis_ready"] = True

    payload = build_industry_peer_analysis(state, documents, include_ai=True)
    state["industry_peer_cache"] = payload
    state["industry_peer_ready"] = True
    state["industry_peer_error"] = ""
    # Final Point-6 risk must be refreshed after Point 10.
    state.pop("risk_assessment_cache", None)
    state["risk_assessment_ready"] = False
    # Existing Point-8 terms may also need rebuilding after the final risk refresh.
    state.pop("loan_terms_cache", None)
    state["loan_terms_ready"] = False
    save_cam(state)
    return jsonify(payload)


@cam_bp.route("/api/cam/loan-terms/<session_id>", methods=["GET", "PUT"])
def cam_loan_terms(session_id):
    """Point-8 Loan Terms & Conditions API.

    GET builds/caches deterministic terms from Points 4-7. PUT stores explicit
    officer overrides, then rebuilds the structured terms.
    """
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    if request.method == "PUT":
        body = request.get_json(silent=True) or {}
        allowed = {"facility_type", "proposed_amount_cr", "tenor_months", "moratorium_months", "interest_rate", "repayment"}
        state["loan_terms_overrides"] = {k: body.get(k) for k in allowed if k in body}
        state.pop("loan_terms_cache", None)
        state.pop("regulatory_compliance_cache", None)
        state["regulatory_compliance_ready"] = False
        state.setdefault("analysis_stages", {})["regulatory_compliance"] = "pending"
        save_cam(state)
    force = str(request.args.get("refresh", "")).lower() in ("1", "true", "yes")
    if state.get("loan_terms_cache") and not force and request.method == "GET":
        return jsonify(state["loan_terms_cache"])
    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return jsonify({"error": "Application not found"}), 404
    documents = [document_payload(d, include_text=True) for d in row.documents]
    db.close()

    # Point 8 consumes prior structured outputs; only build missing dependencies.
    if not state.get("financial_analysis_cache"):
        state["financial_analysis_cache"] = build_financial_analysis(state, documents, include_ai=False)
    if not state.get("credit_history_cache"):
        state["credit_history_cache"] = build_credit_history(state, documents, include_ai=False)
    if not state.get("risk_assessment_cache"):
        state["risk_assessment_cache"] = build_risk_assessment(state, documents, include_ai=False)
    if not state.get("collateral_cache"):
        state["collateral_cache"] = build_collateral_analysis(state, documents, include_ai=False)
    if not state.get("industry_peer_cache"):
        state["industry_peer_cache"] = build_industry_peer_analysis(state, documents, include_ai=False)
        state["industry_peer_ready"] = True
        state.pop("risk_assessment_cache", None)
    # Point 8 must consume the final consolidated risk view after Point 10.
    state["risk_assessment_cache"] = build_risk_assessment(state, documents, include_ai=False)
    state["risk_assessment_ready"] = True

    payload = build_loan_terms(state, documents, include_ai=True)
    state["loan_terms_cache"] = payload
    state["loan_terms_ready"] = True
    state["loan_terms_error"] = ""
    state.pop("regulatory_compliance_cache", None)
    state["regulatory_compliance_ready"] = False
    state.setdefault("analysis_stages", {})["regulatory_compliance"] = "pending"
    save_cam(state)
    return jsonify(payload)


@cam_bp.route("/api/cam/loan-summary/<session_id>", methods=["GET"])
def cam_loan_summary(session_id):
    """Dedicated Step-5 Loan Summary API.

    The response is cached per CAM session to avoid repeating Groq/public-search
    calls when the user navigates away and back. Pass ?refresh=1 after proposal,
    document or external-data changes to rebuild it from current evidence.
    """
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    force = str(request.args.get("refresh", "")).lower() in ("1", "true", "yes")
    if state.get("loan_summary_cache") and not force:
        return jsonify(state["loan_summary_cache"])
    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return jsonify({"error": "Application not found"}), 404
    documents = [document_payload(d, include_text=True) for d in row.documents]
    db.close()
    summary = build_loan_summary(state, documents)

    # Cache only a successful Groq narrative. Failed/not-configured attempts are
    # deliberately not cached so the next Step-5 load can retry after the key,
    # model, network, or provider issue is corrected.
    if summary.get("summary_source") == "ai_generated":
        state["loan_summary_cache"] = summary
        state["loan_summary_ready"] = True
        state["loan_summary_error"] = ""
    else:
        state.pop("loan_summary_cache", None)
        state["loan_summary_ready"] = False
        state["loan_summary_error"] = (summary.get("llm_status") or {}).get("error") or "Groq Loan Summary is not ready."

    save_cam(state)
    return jsonify(summary)


@cam_bp.route("/api/cam/regulatory-compliance/<session_id>", methods=["GET", "POST"])
def cam_regulatory_compliance(session_id):
    """Point-9 deterministic Regulatory & Compliance checks.

    GET returns the saved/current result (or builds it when missing). POST always
    re-runs against the latest CAM, document and policy inputs.
    """
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    force = request.method == "POST" or str(request.args.get("refresh", "")).lower() in ("1", "true", "yes")
    if state.get("regulatory_compliance_cache") and not force:
        return jsonify(state["regulatory_compliance_cache"])
    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return jsonify({"error": "Application not found"}), 404
    documents = [document_payload(d, include_text=True) for d in row.documents]
    db.close()
    if not state.get("loan_terms_cache"):
        return jsonify({"error": "Complete Point 8 Loan Terms & Conditions before running Point 9 compliance checks"}), 400
    payload = build_regulatory_compliance(state, documents)
    state["regulatory_compliance_cache"] = payload
    state["regulatory_compliance_ready"] = True
    state["regulatory_compliance_error"] = ""
    state.setdefault("analysis_stages", {})["regulatory_compliance"] = "completed"
    save_cam(state)
    return jsonify(payload)
