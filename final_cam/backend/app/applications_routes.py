import mimetypes
import os
from flask import Blueprint, jsonify, request, send_file
from app.cam.core import *
from app.cam import storage

applications_bp = Blueprint("applications", __name__)

@applications_bp.route("/api/applications", methods=["POST"])
def create_application_compat():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    loan_type = data.get("loan_type", "msme")
    applicant_name = data.get("applicant_name")
    db = SessionLocal()
    row = LoanApplication(loan_type=loan_type, applicant_name=applicant_name)
    db.add(row)
    db.commit()
    db.refresh(row)
    db.close()
    return jsonify({"application_id": row.id, "loan_type": row.loan_type})
@applications_bp.route("/api/documents/<document_id>/confirm", methods=["POST"])
def confirm_classification(document_id):
    db = SessionLocal()
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        db.close()
        return jsonify({"error": "Document not found"}), 404
    correct_doc_type = request.form.get("correct_doc_type") or (request.get_json(silent=True) or {}).get("correct_doc_type")
    if correct_doc_type and correct_doc_type != doc.doc_type:
        db.add(ClassificationFeedback(
            document_id=doc.id,
            predicted_type=doc.doc_type,
            predicted_score=doc.confidence_score,
            correct_type=correct_doc_type,
            extracted_text_snapshot=doc.extracted_text[:5000] if doc.extracted_text else None,
        ))
        source_path = storage.resolve_document_path(
            doc.storage_path, doc.application_id, doc.stored_filename, doc.original_filename
        )
        if not source_path:
            db.close()
            return jsonify({"error": "Stored document file is not available"}), 404
        new_path = storage.save_upload(source_path, doc.application_id, correct_doc_type, doc.original_filename)
        doc.storage_path = new_path
        doc.stored_filename = os.path.basename(new_path)
        doc.user_corrected_type = correct_doc_type
        doc.doc_type = correct_doc_type
    doc.user_confirmed = True
    doc.status = "confirmed"
    db.commit()
    result = {"document_id": doc.id, "status": doc.status, "doc_type": doc.doc_type}
    db.close()
    return jsonify(result)
@applications_bp.route("/api/documents/<document_id>/file", methods=["GET"])
def preview_document(document_id):
    """Serve an uploaded borrower document inline for the CAM review screen."""
    db = SessionLocal()
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        db.close()
        return jsonify({"error": "Document not found"}), 404
    path = storage.resolve_document_path(
        doc.storage_path,
        application_id=doc.application_id,
        stored_filename=doc.stored_filename,
        original_filename=doc.original_filename,
    )
    filename = doc.original_filename or doc.stored_filename or "document"
    db.close()
    if not path:
        return jsonify({
            "error": "Stored document file is not available",
            "document_id": document_id,
        }), 404
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    response = send_file(
        path,
        mimetype=mime_type,
        as_attachment=False,
        download_name=filename,
        conditional=True,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
@applications_bp.route("/api/documents/<document_id>", methods=["DELETE"])
def delete_document(document_id):
    """Delete one borrower document and its stored file."""
    db = SessionLocal()
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        db.close()
        return jsonify({"error": "Document not found"}), 404

    storage_path = storage.resolve_document_path(
        doc.storage_path,
        application_id=doc.application_id,
        stored_filename=doc.stored_filename,
        original_filename=doc.original_filename,
    )
    try:
        if storage_path and os.path.exists(storage_path):
            os.remove(storage_path)
    except OSError:
        # The DB record is still removed; an orphaned object can be cleaned up
        # by a storage housekeeping job later.
        pass

    db.query(ClassificationFeedback).filter_by(document_id=doc.id).delete(synchronize_session=False)
    db.delete(doc)
    db.commit()
    db.close()
    return jsonify({"document_id": document_id, "deleted": True})
@applications_bp.route("/api/applications/<application_id>/documents", methods=["GET"])
def list_documents_compat(application_id):
    db = SessionLocal()
    docs = db.query(Document).filter_by(application_id=application_id).all()
    result = [document_payload(d) for d in docs]
    db.close()
    return jsonify(result)
@applications_bp.route("/api/applications/<application_id>/progress", methods=["GET"])
def progress_compat(application_id):
    db = SessionLocal()
    row = db.query(LoanApplication).filter_by(id=application_id).first()
    if not row:
        db.close()
        return jsonify({"error": "Application not found"}), 404
    uploaded_types = [d.doc_type for d in row.documents if d.status in ("auto_accepted", "confirmed")]
    progress = compute_progress(row.loan_type, uploaded_types)
    db.close()
    return jsonify(progress)
