from flask import jsonify, request, send_file
from app.cam.blueprint import cam_bp
from app.cam.core import *
from app.cam.llm_gateway import chat as groq_chat, LLMGatewayError
from app.cam.loan_summary import build_loan_summary

@cam_bp.route("/api/cam/template/<session_id>", methods=["POST"])
def cam_template(session_id):
    state=get_cam(session_id)
    if not state: return jsonify({"error":"CAM session not found"}),404
    path=BASE_DIR/"templates"/"bank_cam_master_template.docx"
    if not path.exists(): return jsonify({"error":"Internal bank CAM template is missing"}),500
    state["template"]={"name":path.name,"path":str(path),"internal":True}
    save_cam(state)
    return jsonify({"message":"Internal bank CAM template is configured. No upload required.","template":path.name,"internal":True})
@cam_bp.route("/api/cam/generate/<session_id>", methods=["POST"])
def cam_generate(session_id):
    try:
        generate_cam(session_id)
        state = get_cam(session_id)
        return jsonify({
            "status": "completed",
            "cam_id": state["cam_id"],
            "docx_available": bool(state.get("docx_path")),
            "pdf_available": bool(state.get("pdf_path")),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
@cam_bp.route("/api/cam/download/<session_id>/<file_type>", methods=["GET"])
def cam_download(session_id, file_type):
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404
    path = state.get("docx_path") if file_type == "docx" else state.get("pdf_path") if file_type == "pdf" else None
    if not path or not Path(path).exists():
        return jsonify({"error": f"{file_type.upper()} file is not available"}), 404
    return send_file(path, as_attachment=True, download_name=Path(path).name)
