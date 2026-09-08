from flask import jsonify, request, send_file
from app.cam.blueprint import cam_bp
from app.cam.core import *
from app.cam.llm_gateway import chat as groq_chat, LLMGatewayError
from app.cam.loan_summary import build_loan_summary

@cam_bp.route("/api/cam/document-chat/<session_id>", methods=["POST"])
def cam_document_chat(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    if not state.get("document_sources"):
        return jsonify({"error": "Upload supporting documents first"}), 400
    data = request.get_json(silent=True) or request.form
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    result = answer_question(message, state.get("document_sources", []), state.get("document_chat", []))
    state["document_chat"].append({"role": "user", "content": message})
    state["document_chat"].append({"role": "assistant", "content": result["answer"]})
    save_cam(state)
    return jsonify(result)
@cam_bp.route("/api/cam/documents/<session_id>", methods=["POST"])
def cam_documents(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    # Document upload is intentionally independent of the optional loan-details
    # conversation. A borrower session (created from the mandatory company name)
    # is enough to accept and process uploaded evidence. Loan type, amount,
    # purpose, tenure, pricing and repayment can be captured later.

    files = [f for f in request.files.getlist("file") if f and f.filename]
    if not files:
        return jsonify({"error": "No files selected"}), 400

    db = SessionLocal()
    results = []
    try:
        for file_storage in files:
            filename = secure_filename(file_storage.filename)
            if not filename:
                results.append({"error": "invalid_filename"})
                continue
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in SUPPORTING_EXTENSIONS:
                results.append({
                    "original_filename": filename,
                    "error": "unsupported_file_type",
                    "message": "The current extractor supports PDF and image files."
                })
                continue
            try:
                results.append(process_single_file(db, state["application_id"], file_storage))
            except extraction.OCRUnavailableError as exc:
                results.append({"original_filename": filename, "error": "ocr_unavailable", "message": str(exc)})
            except ValueError as exc:
                results.append({"original_filename": filename, "error": "processing_error", "message": str(exc)})
            except Exception as exc:
                db.rollback()
                results.append({"original_filename": filename, "error": "unexpected_error", "message": str(exc)})
    finally:
        db.close()

    state["conversation_state"] = "analysis"
    state["current_step"] = "Supporting documents processed"
    state["document_sources"] = [
        {
            "filename": r.get("original_filename"),
            "doc_type": r.get("doc_type"),
            "pages": r.get("pages", []),
        }
        for r in results if not r.get("error")
    ]
    save_cam(state)

    # Phase 1 enrichment: if a CIN was extracted, automatically try MCA once.
    # MCA failure never blocks document processing; the UI can retry manually.
    mca_result = None
    cin = discover_cin_for_cam(session_id)
    if cin and os.getenv("MCA_API_KEY", "").strip():
        try:
            mca_result = fetch_mca_for_session(session_id, cin=cin)
        except Exception as exc:
            state = get_cam(session_id)
            state["mca"] = {
                "status": "failed",
                "cin": cin,
                "fetched_at": None,
                "data": None,
                "error": str(exc),
            }
            save_cam(state)

    return jsonify({
        "cam_id": state["cam_id"],
        "application_id": state["application_id"],
        "results": results,
        "mca": mca_result,
        "message": "Documents processed. MCA company data was also fetched when a CIN was available and the MCA API key was configured. Review the information, then start CAM analysis.",
    })
@cam_bp.route("/api/cam/documents/<session_id>", methods=["GET"])
def cam_list_documents(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return jsonify({"error": "Application not found"}), 404
    docs = [document_payload(d) for d in row.documents]
    db.close()
    return jsonify({"documents": docs})
