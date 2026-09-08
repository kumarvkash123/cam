"""
SQLAlchemy models for the KYC/Loan document ingestion POC.

Design notes:
- The raw file itself is NOT stored in the DB. It lives on disk / object storage
  (see storage.py). Only metadata + extracted fields + audit trail live in the DB.
- IDs use String(36) (portable UUID-as-text) instead of Postgres's native UUID
  type, so this works unchanged on SQLite (default/dev) or Postgres (prod) --
  just swap DATABASE_URL, no model changes needed.
- Sensitive fields (Aadhaar number, full PAN, account numbers) are stored masked.
  Add field-level encryption before any production use -- this POC stores
  masked values only, by design.
"""

import uuid
import datetime as dt

from sqlalchemy import (
    Column, String, Float, DateTime, ForeignKey, Text, Integer, JSON, Boolean
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class LoanApplication(Base):
    """One loan application = one user's document upload session."""
    __tablename__ = "loan_applications"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    applicant_name = Column(String, nullable=True)
    loan_type = Column(String, nullable=False, default="msme")  # msme | personal | secured_big_ticket
    loan_amount_bracket = Column(String, nullable=True)  # drives which docs are "mandatory"
    status = Column(String, default="in_progress")  # in_progress | docs_complete | under_review
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    documents = relationship("Document", back_populates="application")


class Document(Base):
    """One uploaded file + its classification result."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    application_id = Column(String(36), ForeignKey("loan_applications.id"))

    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)   # renamed file, e.g. <user_id>_pan.pdf
    storage_path = Column(String, nullable=False)       # path in object storage / disk

    extracted_text = Column(Text, nullable=True)        # full OCR/PDF text (consider truncating/redacting in prod)
    doc_type = Column(String, nullable=True)             # final classified type
    confidence_score = Column(Float, nullable=True)
    classification_method = Column(String, nullable=True)  # "rules" | "llm_fallback" | "user_corrected"
    status = Column(String, default="pending")           # pending | auto_accepted | needs_review | confirmed | rejected

    matched_signals = Column(JSON, nullable=True)         # debug/audit: which rules fired
    candidate_scores = Column(JSON, nullable=True)        # score for every doc_type considered

    extracted_fields = Column(JSON, nullable=True)        # {"pan_number_masked": "ABCDE****F", ...}

    user_confirmed = Column(Boolean, default=False)
    user_corrected_type = Column(String, nullable=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    application = relationship("LoanApplication", back_populates="documents")


class ClassificationFeedback(Base):
    """
    Every user correction gets logged here. This is your active-learning /
    audit trail table -- periodically mine this to tune rule weights in
    rules_config.json.
    """
    __tablename__ = "classification_feedback"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), ForeignKey("documents.id"))
    predicted_type = Column(String, nullable=True)
    predicted_score = Column(Float, nullable=True)
    correct_type = Column(String, nullable=False)
    extracted_text_snapshot = Column(Text, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
