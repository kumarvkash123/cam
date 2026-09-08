from flask import Blueprint, jsonify, render_template, request
from app.cam.core import *

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")
@main_bp.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "integrated-cam-flask"})
@main_bp.route("/api/auth/login", methods=["POST", "OPTIONS"])
def auth_login():
    """POC employee login. Replace this credential check with Bank SSO/MFA in production."""
    if request.method == "OPTIONS":
        return ("", 204)
    payload = request.get_json(silent=True) or {}
    employee_id = str(payload.get("employee_id", "")).strip()
    password = str(payload.get("password", ""))
    expected_id = os.getenv("DEMO_EMPLOYEE_ID", "BOB001")
    expected_password = os.getenv("DEMO_PASSWORD", "ChangeMe123!")
    if not employee_id or not password:
        return jsonify({"error": "Employee ID and password are required."}), 400
    if employee_id != expected_id or password != expected_password:
        return jsonify({"error": "Invalid Employee ID or password."}), 401
    return jsonify({
        "authenticated": True,
        "user": {
            "employee_id": employee_id,
            "name": os.getenv("DEMO_EMPLOYEE_NAME", "Credit Officer"),
            "role": "Credit Officer",
        },
        "message": "Login successful",
    })
@main_bp.route("/api/dashboard", methods=["GET"])
def dashboard():
    """Return live CAM overview data from the local SQL database."""
    db = SessionLocal()
    try:
        applications = db.query(LoanApplication).order_by(LoanApplication.created_at.desc()).all()
        total = len(applications)
        in_progress = sum(1 for a in applications if a.status in (None, "in_progress", "docs_complete"))
        under_review = sum(1 for a in applications if a.status == "under_review")
        completed = sum(1 for a in applications if a.status in ("completed", "approved"))
        docs = db.query(Document).all()
        docs_processed = len(docs)
        docs_needing_review = sum(1 for d in docs if d.status in ("needs_review", "low_confidence"))
        type_counts = {}
        for a in applications:
            key = (a.loan_type or "other").replace("_", " ").title()
            type_counts[key] = type_counts.get(key, 0) + 1
        recent = []
        for a in applications[:8]:
            recent.append({
                "application_id": a.id,
                "cam_id": f"CAM-{a.created_at.strftime('%Y%m%d')}-{a.id[:6].upper()}" if a.created_at else f"CAM-{a.id[:6].upper()}",
                "company": a.applicant_name or "Unnamed Borrower",
                "loan_type": (a.loan_type or "—").replace("_", " ").title(),
                "status": a.status or "in_progress",
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })
        return jsonify({
            "metrics": {
                "total_proposals": total,
                "in_progress": in_progress,
                "under_review": under_review,
                "completed": completed,
                "overdue": 0,
                "documents_processed": docs_processed,
                "documents_review": docs_needing_review,
            },
            "loan_type_distribution": type_counts,
            "recent_proposals": recent,
            "active_sessions": len(CAM_SESSIONS),
            "generated_at": now_iso(),
        })
    finally:
        db.close()
