from flask import jsonify, request, send_file
from app.cam.blueprint import cam_bp
from app.cam.core import *
from app.cam.llm_gateway import chat as groq_chat, LLMGatewayError
from app.cam.loan_summary import build_loan_summary

@cam_bp.route("/api/cam/mca/<session_id>", methods=["POST"])
def cam_mca_fetch(session_id):
    """Fetch MCA company master data using a CIN from documents or request body."""
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404

    data = request.get_json(silent=True) or request.form
    cin = str(data.get("cin", "")).strip() if data else ""
    try:
        mca = fetch_mca_for_session(session_id, cin=cin or None)
        return jsonify({
            "status": "completed",
            "cin": mca["cin"],
            "fetched_at": mca["fetched_at"],
            "data": mca["data"],
            "message": "MCA company data fetched successfully.",
        })
    except (ValueError, RuntimeError) as exc:
        state = get_cam(session_id)
        if state:
            state["mca"] = {
                "status": "failed",
                "cin": cin or discover_cin_for_cam(session_id),
                "fetched_at": None,
                "data": None,
                "error": str(exc),
            }
            save_cam(state)
        return jsonify({"status": "failed", "error": str(exc)}), 400
    except Exception as exc:
        state = get_cam(session_id)
        if state:
            state["mca"] = {
                "status": "failed",
                "cin": cin or discover_cin_for_cam(session_id),
                "fetched_at": None,
                "data": None,
                "error": "Unexpected MCA integration error",
            }
            save_cam(state)
        return jsonify({"status": "failed", "error": "Unexpected MCA integration error"}), 500
@cam_bp.route("/api/cam/mca/<session_id>", methods=["GET"])
def cam_mca_status(session_id):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    return jsonify(state.get("mca", {"status": "not_fetched"}))
