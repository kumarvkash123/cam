import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import requests
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.utils import secure_filename
from docx import Document as DocxDocument

# Load .env BEFORE importing services that read environment variables.
from app.config import BASE_DIR, get_groq_api_key, get_groq_model, get_mca_api_key

from app.database import SessionLocal, init_db
from app.models import LoanApplication, Document, ClassificationFeedback
from app.cam import extraction, classifier, field_extraction, storage
from app.cam.requirement_matrix import compute_progress
from app.cam import mca_service
from app.cam.report_builder import build_cam_reports
from app.cam.loan_summary import build_loan_summary
from app.cam.borrower_info import build_borrower_profile
from app.cam.business_overview import build_business_overview
from app.cam.financial_analysis import build_financial_analysis
from app.cam.credit_history import build_credit_history
from app.cam.risk_assessment import build_risk_assessment
from app.cam.collateral import build_collateral_analysis
from app.cam.loan_terms import build_loan_terms
from app.cam.industry_peer import build_industry_peer_analysis
from app.cam.regulatory_compliance import build_regulatory_compliance
from app.cam.llm_service import generate_cam_narratives
from app.cam.rag_chat import answer_question
from app.cam.response_formatter import format_assistant_response
from app.cam.normalized import build_normalized_cam_data
from app.cam.final_cam import build_twenty_page_cam
from app.cam.web_search import google_search
from docx import Document as DocxDocument
from docx.shared import Pt



# The UI is a separate Next.js application (default: http://localhost:3000).
# Keep the backend API independently deployable and allow only configured
# frontend origins instead of using a wildcard CORS policy.

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# The extractor/classifier in the existing KYC POC is reused directly.
# Keep this list aligned with extraction.py; unsupported files are reported
# per-file instead of stopping a multi-file upload.
SUPPORTING_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"
}
TEMPLATE_EXTENSIONS = {"docx", "dotx"}
POLICY_EXTENSIONS = {"pdf", "docx", "doc", "pptx", "txt", "png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"}

ANALYSIS_STEPS = [
    ("loan_summary", "Loan Summary"),
    ("borrower_information", "Borrower Information"),
    ("business_overview", "Business Overview"),
    ("financial_analysis", "Financial Analysis"),
    ("credit_history", "Credit History"),
    ("risk_assessment", "Risk Assessment & Mitigation"),
    ("collateral", "Collateral Details"),
    ("loan_terms", "Loan Terms & Conditions"),
    ("compliance", "Regulatory Compliance"),
    ("benchmarking", "Peer / Market Benchmarking"),
]

# POC-only CAM state. The documents and their extracted fields are persisted
# in the existing SQLAlchemy DB. This dictionary holds conversational/session
# fields that we have not added to the existing DB schema yet.
CAM_SESSIONS = {}
CAM_LOCK = threading.Lock()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_cam_session(company_name):
    session_id = uuid.uuid4().hex[:12]
    steps = [{"key": k, "label": label, "status": "pending"} for k, label in ANALYSIS_STEPS]
    state = {
        "session_id": session_id,
        "cam_id": f"CAM-{datetime.now().strftime('%Y%m%d')}-{session_id.upper()}",
        "company_name": company_name.strip(),
        "loan_type": "",
        "loan_amount": "",
        "loan_amount_numeric": None,
        "loan_purpose": "",
        "tenure": "",
        "interest_rate": "",
        "repayment": "",
        "conversation_state": "assistant",
        "status": "collecting",
        "progress": 0,
        "current_step": "CAM Assistant ready",
        "steps": steps,
        "template": {"name": "bank_cam_master_template.docx", "internal": True},
        "policy_sources": [],
        "policy_chat": [],
        "policy_review_completed": False,
        "policy_review_completed_at": None,
        "document_sources": [],
        "document_chat": [],
        "assistant_chat": [],
        "docx_path": None,
        "pdf_path": None,
        "error": "",
        "mca": {
            "status": "not_fetched",
            "cin": None,
            "fetched_at": None,
            "data": None,
            "error": None,
        },
        "created_at": now_iso(),
        "reports": [],
    }
    with CAM_LOCK:
        CAM_SESSIONS[session_id] = state
    return state


def get_cam(session_id):
    with CAM_LOCK:
        return CAM_SESSIONS.get(session_id)


def save_cam(state):
    with CAM_LOCK:
        CAM_SESSIONS[state["session_id"]] = state


def parse_amount(value):
    if value is None:
        return None
    text = str(value).strip().lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "")
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(crore|cr|lakh|lac|million|mn|k)?", text)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2) or ""
    if unit in ("crore", "cr"):
        number *= 10_000_000
    elif unit in ("lakh", "lac"):
        number *= 100_000
    elif unit in ("million", "mn"):
        number *= 1_000_000
    elif unit == "k":
        number *= 1_000
    return number


def loan_type_normalize(value):
    text = str(value or "").strip().lower()
    aliases = {
        "msme loan": "msme",
        "business loan": "msme",
        "working capital": "msme",
        "personal loan": "personal",
        "secured loan": "secured_big_ticket",
        "big ticket": "secured_big_ticket",
        "big-ticket": "secured_big_ticket",
    }
    return aliases.get(text, text)


def get_db_application(session_id):
    state = get_cam(session_id)
    if not state:
        return None, None
    db = SessionLocal()
    row = db.query(LoanApplication).filter_by(id=state.get("application_id")).first()
    return db, row


def sync_cam_to_db(state):
    db, row = get_db_application(state["session_id"])
    if not row:
        if db:
            db.close()
        return
    row.applicant_name = state["company_name"]
    if state.get("loan_type"):
        row.loan_type = state["loan_type"]
    amount = state.get("loan_amount_numeric")
    if amount is not None:
        if amount >= 10_000_000:
            row.loan_amount_bracket = "10cr+"
        elif amount >= 10_000_000 * 0.5:
            row.loan_amount_bracket = "5cr-10cr"
        elif amount >= 10_000_000 * 0.1:
            row.loan_amount_bracket = "1cr-5cr"
        else:
            row.loan_amount_bracket = "<1cr"
    db.commit()
    db.close()


def process_single_file(db, application_id, file_storage):
    """Reuse the existing extraction -> classification -> field extraction pipeline."""
    original_filename = secure_filename(file_storage.filename)
    suffix = os.path.splitext(original_filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file_storage.save(tmp.name)
        tmp_path = tmp.name

    try:
        extraction_result = extraction.extract_document(tmp_path)
        text = extraction_result["text"]
        layout = extraction_result["layout"]

        print("\n" + "=" * 70)
        print(f"[CAM EXTRACTION] file: {original_filename}")
        print(f"[CAM EXTRACTION] method: {extraction_result.get('extraction_method')}")
        print(f"[CAM EXTRACTION] characters: {len(text or '')}")
        print("=" * 70 + "\n")

        result = classifier.classify(text, layout, filename=original_filename)
        status = "low_confidence" if result.decision == "llm_fallback" else result.decision
        fields = field_extraction.extract_fields(result.doc_type, text)

        stored_path = storage.save_upload(
            tmp_path, application_id, result.doc_type, original_filename
        )

        doc_row = Document(
            application_id=application_id,
            original_filename=original_filename,
            stored_filename=os.path.basename(stored_path),
            storage_path=stored_path,
            extracted_text=text[:500000],
            doc_type=result.doc_type,
            confidence_score=result.score,
            classification_method="rules",
            status=status,
            matched_signals=result.matched_signals,
            candidate_scores=result.all_candidates,
            extracted_fields=fields,
        )
        db.add(doc_row)
        db.commit()
        db.refresh(doc_row)

        return {
            "original_filename": original_filename,
            "document_id": doc_row.id,
            "stored_filename": doc_row.stored_filename,
            "doc_type": doc_row.doc_type,
            "display_name": result.display_name,
            "confidence_score": doc_row.confidence_score,
            "status": doc_row.status,
            "classification_method": "rules",
            "extracted_fields": fields,
            "top_candidates": result.all_candidates,
            "extraction_method": extraction_result.get("extraction_method"),
            "pages": extraction_result.get("pages", []),
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def extract_policy_source(file_storage, application_id):
    """Extract a policy file while preserving page/source boundaries for citations."""
    original_filename = secure_filename(file_storage.filename)
    suffix = os.path.splitext(original_filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file_storage.save(tmp.name)
        tmp_path = tmp.name
    try:
        if suffix in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
            result = extraction.extract_document(tmp_path)
            pages = result.get("pages", [])
            text = result.get("text", "")
        elif suffix == ".txt":
            text = Path(tmp_path).read_text(encoding="utf-8", errors="ignore")
            pages = [{"page_no": 1, "text": text, "words": []}]
        elif suffix in {".docx", ".doc"}:
            if suffix == ".doc":
                raise ValueError("Legacy .doc policy files are not supported; save the policy as DOCX or PDF.")
            d = DocxDocument(tmp_path)
            paragraphs = [p.text for p in d.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
            for table in d.tables:
                for row in table.rows:
                    text += "\n" + " | ".join(cell.text for cell in row.cells)
            pages = [{"page_no": 1, "text": text, "words": []}]
        elif suffix == ".pptx":
            from pptx import Presentation
            prs = Presentation(tmp_path)
            page_text = []
            for idx, slide in enumerate(prs.slides, start=1):
                parts = []
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        parts.append(shape.text)
                page_text.append({"page_no": idx, "text": "\n".join(parts), "words": []})
            pages = page_text
            text = "\n".join(p["text"] for p in pages)
        else:
            raise ValueError("Unsupported policy file type")
        policy_dir = UPLOAD_DIR / str(application_id) / "policies"
        policy_dir.mkdir(parents=True, exist_ok=True)
        stored = policy_dir / f"{uuid.uuid4().hex}_{original_filename}"
        shutil.copy2(tmp_path, stored)
        return {
            "filename": original_filename,
            "stored_path": str(stored),
            "category": "Policy Document",
            "status": "indexed",
            "text": text,
            "pages": pages,
            "page_count": len(pages),
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def document_payload(doc, include_text=False):
    display = doc.doc_type.replace("_", " ").title() if doc.doc_type else "Unknown"
    return {
        "document_id": doc.id,
        "original_filename": doc.original_filename,
        "stored_filename": doc.stored_filename,
        "doc_type": doc.doc_type,
        "display_name": display,
        "confidence_score": doc.confidence_score,
        "status": doc.status,
        "classification_method": doc.classification_method,
        "extraction_method": None,
        "extracted_fields": doc.extracted_fields or {},
        "top_candidates": doc.candidate_scores or [],
        **({"extracted_text": doc.extracted_text or ""} if include_text else {}),
    }


def discover_cin_for_cam(session_id):
    """Find the first CIN extracted from uploaded documents."""
    state = get_cam(session_id)
    if not state:
        return None
    db, row = get_db_application(session_id)
    if not row:
        if db:
            db.close()
        return None
    cin = None
    for doc in row.documents:
        fields = doc.extracted_fields or {}
        cin = mca_service.find_cin_in_value(fields)
        if cin:
            break
    if db:
        db.close()
    return cin


def fetch_mca_for_session(session_id, cin=None):
    state = get_cam(session_id)
    if not state:
        raise ValueError("CAM session not found")

    cin = cin or discover_cin_for_cam(session_id)
    if not cin:
        raise ValueError("CIN was not found in the uploaded documents. Upload a Certificate of Incorporation / MCA document containing the CIN, or enter the CIN manually.")

    state["mca"] = {
        "status": "fetching",
        "cin": cin,
        "fetched_at": None,
        "data": None,
        "error": None,
    }
    save_cam(state)

    payload = mca_service.get_company_by_cin_with_fallback(cin, allow_synthetic=True)

    state = get_cam(session_id)
    meta = payload.get("_meta", {}) if isinstance(payload, dict) else {}
    state["mca"] = {
        "status": "completed",
        "cin": cin,
        "fetched_at": now_iso(),
        "data": payload,
        "error": None,
        "source": meta.get("provider") or "FileSure / MCA",
        "synthetic": bool(meta.get("synthetic")),
    }
    save_cam(state)
    return state["mca"]


def process_analysis(session_id):
    """Prepare the Loan Summary first, then continue remaining CAM work in background."""
    state = get_cam(session_id)
    if not state:
        return
    try:
        state['status'] = 'processing'
        state['progress'] = 5
        state['current_step'] = 'Loading verified application evidence'
        state['loan_summary_ready'] = False
        state['loan_summary_error'] = ''
        state['analysis_stages'] = {
            'evidence': 'running', 'financial': 'pending', 'credit_risk': 'pending',
            'collateral_compliance': 'pending', 'loan_summary': 'pending',
            'borrower_information': 'pending', 'business_overview': 'pending',
            'financial_analysis': 'pending', 'credit_history': 'pending',
            'risk_assessment': 'pending', 'collateral': 'pending',
            'industry_peer': 'pending', 'loan_terms': 'pending',
            'regulatory_compliance': 'pending', 'remaining_cam': 'pending'
        }
        save_cam(state)

        db, row = get_db_application(session_id)
        if not row:
            if db: db.close()
            raise ValueError('Application not found')
        documents = [document_payload(d, include_text=True) for d in row.documents]
        db.close()

        # Build one source-of-truth bundle: uploaded raw evidence -> FileSure/synthetic verification -> deterministic calculations.
        normalized = build_normalized_cam_data(state, documents)
        state = get_cam(session_id)
        state['normalized_cam_data'] = normalized
        state['verification_bundle'] = normalized.get('verification')
        save_cam(state)

        state = get_cam(session_id); state['analysis_stages']['evidence']='completed'; state['analysis_stages']['financial']='running'; state['progress']=20; state['current_step']='Preparing financial evidence'; save_cam(state)
        # Loan Summary builder performs deterministic financial/risk normalization before Groq narration.
        state = get_cam(session_id); state['analysis_stages']['financial']='completed'; state['analysis_stages']['credit_risk']='running'; state['progress']=35; state['current_step']='Preparing credit and risk evidence'; save_cam(state)
        state = get_cam(session_id); state['analysis_stages']['credit_risk']='completed'; state['analysis_stages']['collateral_compliance']='running'; state['progress']=48; state['current_step']='Preparing collateral and compliance evidence'; save_cam(state)
        state = get_cam(session_id); state['analysis_stages']['collateral_compliance']='completed'; state['analysis_stages']['loan_summary']='running'; state['progress']=58; state['current_step']='Generating Loan Summary with Groq'; save_cam(state)

        summary = build_loan_summary(state, documents)
        state = get_cam(session_id)
        if summary.get('summary_source') == 'ai_generated' and summary.get('executive_summary'):
            state['loan_summary_cache'] = summary
            state['loan_summary_ready'] = True
            state['loan_summary_error'] = ''
            state['analysis_stages']['loan_summary'] = 'completed'
        else:
            state.pop('loan_summary_cache', None)
            state['loan_summary_ready'] = False
            state['loan_summary_error'] = (summary.get('llm_status') or {}).get('error') or 'Groq Loan Summary generation failed.'
            state['analysis_stages']['loan_summary'] = 'failed'
        state['analysis_stages']['borrower_information'] = 'running'
        state['analysis_stages']['remaining_cam'] = 'running'
        state['progress'] = 68
        state['current_step'] = 'Preparing Borrower Information in background'
        save_cam(state)

        # Step 6 enrichment runs in the same background pipeline while the officer reviews Step 5.
        try:
            borrower_profile = build_borrower_profile(state, documents, include_ai=True)
            state = get_cam(session_id)
            state['borrower_information_cache'] = borrower_profile
            state['borrower_information_ready'] = True
            state['analysis_stages']['borrower_information'] = 'completed'
        except Exception as borrower_exc:
            state = get_cam(session_id)
            state['borrower_information_ready'] = False
            state['borrower_information_error'] = str(borrower_exc)
            state['analysis_stages']['borrower_information'] = 'failed'
        state['analysis_stages']['business_overview'] = 'running'
        state['progress'] = 76
        state['current_step'] = 'Preparing Business Overview in background'
        save_cam(state)

        # Step 7 is prepared while the officer reviews Borrower Information.
        try:
            business_overview = build_business_overview(state, documents, include_ai=True)
            state = get_cam(session_id)
            state['business_overview_cache'] = business_overview
            state['business_overview_ready'] = True
            state['business_overview_error'] = ''
            state['analysis_stages']['business_overview'] = 'completed'
        except Exception as business_exc:
            state = get_cam(session_id)
            state['business_overview_ready'] = False
            state['business_overview_error'] = str(business_exc)
            state['analysis_stages']['business_overview'] = 'failed'
        state['analysis_stages']['financial_analysis'] = 'running'
        state['progress'] = 80
        state['current_step'] = 'Preparing Financial Analysis & Stress Testing in background'
        save_cam(state)

        # Point 4 financial analysis is deterministic. Groq only phrases the already-calculated commentary.
        try:
            financial_analysis = build_financial_analysis(state, documents, include_ai=True)
            state = get_cam(session_id)
            state['financial_analysis_cache'] = financial_analysis
            state['financial_analysis_ready'] = True
            state['financial_analysis_error'] = ''
            state['analysis_stages']['financial_analysis'] = 'completed'
        except Exception as financial_exc:
            state = get_cam(session_id)
            state['financial_analysis_ready'] = False
            state['financial_analysis_error'] = str(financial_exc)
            state['analysis_stages']['financial_analysis'] = 'failed'
        state['analysis_stages']['credit_history'] = 'running'
        state['progress'] = 84
        state['current_step'] = 'Preparing Credit History & Repayment Track Record in background'
        save_cam(state)

        try:
            credit_history = build_credit_history(state, documents, include_ai=True)
            state = get_cam(session_id)
            state['credit_history_cache'] = credit_history
            state['credit_history_ready'] = True
            state['credit_history_error'] = ''
            state['analysis_stages']['credit_history'] = 'completed'
        except Exception as credit_exc:
            state = get_cam(session_id)
            state['credit_history_ready'] = False
            state['credit_history_error'] = str(credit_exc)
            state['analysis_stages']['credit_history'] = 'failed'

        state['analysis_stages']['risk_assessment'] = 'running'
        state['progress'] = 87
        state['current_step'] = 'Consolidating Risk Assessment & Mitigation in background'
        save_cam(state)
        try:
            risk_assessment = build_risk_assessment(state, documents, include_ai=True)
            state = get_cam(session_id)
            state['risk_assessment_cache'] = risk_assessment
            state['risk_assessment_ready'] = True
            state['risk_assessment_error'] = ''
            state['analysis_stages']['risk_assessment'] = 'completed'
        except Exception as risk_exc:
            state = get_cam(session_id)
            state['risk_assessment_ready'] = False
            state['risk_assessment_error'] = str(risk_exc)
            state['analysis_stages']['risk_assessment'] = 'failed'

        state['analysis_stages']['collateral'] = 'running'
        state['progress'] = 90
        state['current_step'] = 'Preparing Collateral Details in background'
        save_cam(state)
        try:
            collateral = build_collateral_analysis(state, documents, include_ai=True)
            state = get_cam(session_id)
            state['collateral_cache'] = collateral
            state['collateral_ready'] = True
            state['collateral_error'] = ''
            state['analysis_stages']['collateral'] = 'completed'
            state.pop('risk_assessment_cache', None)
            state['risk_assessment_ready'] = False
        except Exception as collateral_exc:
            state = get_cam(session_id)
            state['collateral_ready'] = False
            state['collateral_error'] = str(collateral_exc)
            state['analysis_stages']['collateral'] = 'failed'

        # Point 10 is deliberately executed after Point 7 and before final risk / Point 8.
        # This completes the analytical picture with market and peer context.
        state['analysis_stages']['industry_peer'] = 'running'
        state['progress'] = 92
        state['current_step'] = 'Preparing Industry, Market & Peer Analysis in background'
        save_cam(state)
        try:
            industry_peer = build_industry_peer_analysis(state, documents, include_ai=True)
            state = get_cam(session_id)
            state['industry_peer_cache'] = industry_peer
            state['industry_peer_ready'] = True
            state['industry_peer_error'] = ''
            state['analysis_stages']['industry_peer'] = 'completed'
            # Point 10 can alter the final consolidated risk view.
            state.pop('risk_assessment_cache', None)
            state['risk_assessment_ready'] = False
        except Exception as industry_exc:
            state = get_cam(session_id)
            state['industry_peer_ready'] = False
            state['industry_peer_error'] = str(industry_exc)
            state['analysis_stages']['industry_peer'] = 'failed'

        state['analysis_stages']['loan_terms'] = 'running'
        state['progress'] = 94
        state['current_step'] = 'Refreshing consolidated risk and preparing Loan Terms & Conditions'
        save_cam(state)
        try:
            # Final consolidated risk now sees Point 7 collateral + Point 10 industry/peer evidence.
            state['risk_assessment_cache'] = build_risk_assessment(state, documents, include_ai=False)
            state['risk_assessment_ready'] = True
            loan_terms = build_loan_terms(state, documents, include_ai=True)
            state = get_cam(session_id)
            state['loan_terms_cache'] = loan_terms
            state['loan_terms_ready'] = True
            state['loan_terms_error'] = ''
            state['analysis_stages']['loan_terms'] = 'completed'
        except Exception as loan_terms_exc:
            state = get_cam(session_id)
            state['loan_terms_ready'] = False
            state['loan_terms_error'] = str(loan_terms_exc)
            state['analysis_stages']['loan_terms'] = 'failed'

        # Point 9 runs only after Point 8. It can also be explicitly re-run from the UI.
        state['analysis_stages']['regulatory_compliance'] = 'running'
        state['progress'] = 96
        state['current_step'] = 'Running Regulatory & Compliance checks'
        save_cam(state)
        try:
            compliance = build_regulatory_compliance(state, documents)
            state = get_cam(session_id)
            state['regulatory_compliance_cache'] = compliance
            state['regulatory_compliance_ready'] = True
            state['regulatory_compliance_error'] = ''
            state['analysis_stages']['regulatory_compliance'] = 'completed'
        except Exception as compliance_exc:
            state = get_cam(session_id)
            state['regulatory_compliance_ready'] = False
            state['regulatory_compliance_error'] = str(compliance_exc)
            state['analysis_stages']['regulatory_compliance'] = 'failed'

        state['progress'] = 97
        state['current_step'] = 'Preparing remaining CAM sections'
        save_cam(state)

        # Continue the detailed CAM reports while the officer reviews the prepared modules.
        state = get_cam(session_id)
        state['reports'] = build_cam_reports(state, documents)
        state['progress'] = 96; state['current_step'] = 'Generating detailed CAM narratives'; save_cam(state)
        state['ai_narratives'] = generate_cam_narratives(state, documents, state['reports'])
        state['risk_findings'] = []
        state['policy_checks'] = []
        for step in state['steps']:
            step['status'] = 'completed'
        state['analysis_stages']['remaining_cam'] = 'completed'
        state['status'] = 'analysis_completed'
        state['current_step'] = 'CAM analysis completed'
        state['progress'] = 100
        save_cam(state)
    except Exception as exc:
        state = get_cam(session_id)
        if state:
            state['status'] = 'failed'
            state['error'] = str(exc)
            save_cam(state)


def copy_template(template_path=None):
    path = Path(template_path) if template_path else BASE_DIR / "templates" / "bank_cam_master_template.docx"
    return DocxDocument(str(path))

def _fmt(v):
    if v is None or v == "": return "Not available"
    if isinstance(v, (dict,list)): return json.dumps(v, ensure_ascii=False, indent=2)
    return str(v)

def _table(doc, rows, headers=None):
    if headers:
        rows=[headers]+rows
    if not rows: return
    t=doc.add_table(rows=len(rows), cols=max(len(r) for r in rows))
    t.style='Table Grid' if 'Table Grid' in [x.name for x in doc.styles] else 'Normal Table'
    for i,row in enumerate(rows):
        for j,val in enumerate(row):
            t.cell(i,j).text=_fmt(val)
            for p in t.cell(i,j).paragraphs:
                for r in p.runs: r.font.size=Pt(8.5)
    doc.add_paragraph()

def _section(doc,title,level=1):
    doc.add_heading(title,level=level)

def _source_facts(doc, documents):
    _section(doc,'Supporting Document Register',2)
    rows=[]
    for d in documents:
        rows.append([d.get('original_filename',''),d.get('display_name',''),d.get('confidence_score',''),d.get('status','')])
    _table(doc,rows,['Document','Type','Confidence','Status'])

def _all_fields(documents):
    out={}
    for d in documents:
        for k,v in (d.get('extracted_fields') or {}).items(): out[k]=v
    return out

def _find(fields,*names):
    for n in names:
        if n in fields and fields[n] not in (None,'','Not available'): return fields[n]
    return None

def _financial_rows(fields):
    keys=[('Revenue','revenue'),('EBITDA','ebitda'),('PAT','pat'),('Tangible Net Worth','tangible_net_worth'),('Adjusted TNW','adjusted_tnw'),('Term Loan','term_loan'),('Capital Employed','capital_employed'),('Current Assets','current_assets'),('Current Liabilities','current_liabilities'),('Total Debt','total_debt'),('Interest','interest')]
    years=[]
    for k in fields:
        m=re.search(r'(20\d{2}(?:-\d{2})?)$',str(k))
        if m and m.group(1) not in years: years.append(m.group(1))
    years=sorted(years)
    rows=[]
    for label,prefix in keys:
        vals=[]
        for y in years:
            v=_find(fields,f'{prefix}_{y}',f'{prefix}{y}')
            vals.append(v if v is not None else '—')
        if vals: rows.append([label]+vals)
    return years,rows

def _ratio(a,b):
    try:
        return round(float(a)/float(b),2) if float(b)!=0 else None
    except: return None

def build_detailed_cam_document(state,documents):
    doc=copy_template()
    # remove placeholder starter paragraph if present
    body=doc._element.body
    for p in list(doc.paragraphs):
        if 'BANK CAM MASTER TEMPLATE' in p.text or 'CREDIT APPRAISAL MEMORANDUM' in p.text:
            try: body.remove(p._element)
            except: pass
    fields=_all_fields(documents)
    mca=(state.get('mca') or {}).get('data') or {}
    doc.add_heading('NOTE TO DGM BUSINESS DEVELOPMENT / CREDIT COMMITTEE',0)
    doc.add_paragraph('Issue for consideration: appraisal of the proposed credit facilities based on the documents, registry information, financial evidence and policy checks available in the application.')
    _table(doc,[['CAM ID',state.get('cam_id')],['Borrower',state.get('company_name')],['Loan Type',state.get('loan_type')],['Requested Amount',state.get('loan_amount')],['Purpose',state.get('loan_purpose')],['Tenure',state.get('tenure')],['Interest Rate',state.get('interest_rate')],['Repayment',state.get('repayment')],['Generated',datetime_now()]],['Particular','Details'])

    _section(doc,'1. EXECUTIVE SUMMARY',1)
    doc.add_paragraph(state.get('ai_narratives',{}).get('executive_summary') or 'The proposal has been assessed using the evidence uploaded to the CAM application. Facts not available in the source documents are explicitly identified as not available and are not assumed.')
    _section(doc,'2. ISSUE FOR CONSIDERATION',2)
    doc.add_paragraph(f"To consider the requested {state.get('loan_type') or 'credit facility'} of {state.get('loan_amount') or 'the proposed amount'} for {state.get('company_name')}. The final recommendation remains subject to document verification, applicable policy and credit authority approval.")
    _section(doc,'3. BORROWER INFORMATION',1)
    _table(doc,[[k,_fmt(v)] for k,v in list(fields.items())[:40]],['Extracted field','Value'])
    _section(doc,'3.1 MCA / COMPANY MASTER INFORMATION',2)
    if mca:
        flat=[]
        def walk(x,p=''):
            if isinstance(x,dict):
                for k,v in x.items(): walk(v,f'{p}.{k}' if p else k)
            elif isinstance(x,list):
                for i,v in enumerate(x[:20]): walk(v,f'{p}[{i}]')
            else: flat.append([p,_fmt(x)])
        walk(mca)
        _table(doc,flat[:100],['MCA Field','Value'])
    else: doc.add_paragraph('MCA data not available. Configure FileSure credentials and provide a valid CIN to fetch registry data.')
    _section(doc,'3.2 SHAREHOLDING, DIRECTORS, GUARANTORS AND GROUP',2)
    doc.add_paragraph('The following information is derived from uploaded corporate documents and MCA data where available.')
    _table(doc,[[k,_fmt(v)] for k,v in fields.items() if any(x in k.lower() for x in ['director','share','promoter','guarant','group','associate'])][:80],['Particular','Value'])

    _section(doc,'4. BANKING ARRANGEMENT',1)
    _table(doc,[[k,_fmt(v)] for k,v in fields.items() if any(x in k.lower() for x in ['bank','facility','cc','od','term_loan','limit','outstanding'])][:80],['Banking / Facility Field','Value'])
    _section(doc,'5. CONDUCT, COMPLIANCE AND VALUE OF ACCOUNT',1)
    doc.add_paragraph(state.get('ai_narratives',{}).get('conduct') or 'Account conduct assessment is based only on uploaded banking and credit evidence.')
    _table(doc,[[k,_fmt(v)] for k,v in fields.items() if any(x in k.lower() for x in ['cibil','crif','sma','repayment','overdue','default','fraud','roc','legal'])][:100],['Credit / Compliance Evidence','Value'])

    _section(doc,'6. FINANCIALS',1)
    years,rows=_financial_rows(fields)
    if rows: _table(doc,rows,['Financial Particular']+years)
    else: doc.add_paragraph('Structured financial line items were not sufficiently extracted from the uploaded financial statements.')
    _section(doc,'6.1 NOTES TO FINANCIALS',2)
    _table(doc,[[k,_fmt(v)] for k,v in fields.items() if any(x in k.lower() for x in ['asset','liabil','inventory','debtor','creditor','cash','reserve','capital'])][:120],['Financial Field','Value'])
    _section(doc,'6.2 FINANCIAL RATIOS AND ASSESSMENT',2)
    cr=_ratio(_find(fields,'current_assets'),_find(fields,'current_liabilities'))
    de=_ratio(_find(fields,'total_debt','term_liabilities'),_find(fields,'adjusted_tnw','tangible_net_worth'))
    icr=_ratio(_find(fields,'ebitda'),_find(fields,'interest'))
    _table(doc,[['Current Ratio',cr or 'Not available'],['Debt / Adjusted TNW',de or 'Not available'],['Interest Coverage',icr or 'Not available'],['DSCR',_find(fields,'dscr') or 'Not available'],['Debt / EBITDA',_find(fields,'debt_ebitda') or 'Not available']],['Ratio','Computed / Extracted Value'])
    _section(doc,'6.3 CASH FLOW / FUND FLOW',2)
    doc.add_paragraph(state.get('ai_narratives',{}).get('cash_flow') or 'Cash-flow assessment is based on extracted financial and banking evidence.')
    _section(doc,'6.4 STRESS TESTING',2)
    doc.add_paragraph('Stress testing is deterministic and illustrative. It is not a credit decision.')
    _table(doc,[['Base Case','No stress'],['Revenue -10%','Revenue reduced by 10%; profitability and servicing metrics should be recalculated from verified values'],['Revenue -20%','Revenue reduced by 20%; assess impact on EBITDA/PAT and debt servicing'],['Interest +2%','Interest burden increased by 2 percentage points where applicable'],['Combined','Revenue -20% with interest +2%']],['Scenario','Assessment'])

    _section(doc,'7. MAJOR COUNTERPARTIES AND BUSINESS OVERVIEW',1)
    doc.add_paragraph(state.get('ai_narratives',{}).get('business_overview') or 'Business overview is generated from the borrower proposal and extracted documents.')
    _table(doc,[[k,_fmt(v)] for k,v in fields.items() if any(x in k.lower() for x in ['customer','buyer','supplier','product','industry','business','turnover','sales','capacity'])][:120],['Business Evidence','Value'])

    _section(doc,'8. RISK MITIGATION STRATEGIES & SECURITIES',1)
    _section(doc,'8.1 KEY RISKS & MITIGATION',2)
    for item in state.get('risk_findings',[]): doc.add_paragraph(f"Risk: {item.get('risk','')} — Mitigation: {item.get('mitigation','')}")
    if not state.get('risk_findings'): doc.add_paragraph('No automated risk finding was produced beyond the evidence currently available.')
    _section(doc,'8.2 SECURITIES / COLLATERAL',2)
    _table(doc,[[k,_fmt(v)] for k,v in fields.items() if any(x in k.lower() for x in ['property','security','collateral','valuation','mortgage','charge','guarantee','tcr'])][:150],['Security Evidence','Value'])

    _section(doc,'9. ASSESSMENT / JUSTIFICATION FOR PROPOSED CREDIT FACILITIES',1)
    doc.add_paragraph(state.get('ai_narratives',{}).get('assessment') or 'Assessment is based on verified application evidence, deterministic financial analysis and policy outcomes.')
    _section(doc,'9.1 LOAN ASSESSMENT',2)
    _table(doc,[[k,_fmt(v)] for k,v in fields.items() if any(x in k.lower() for x in ['mpbf','drawing','working_capital','cash_accrual','assessment','limit','margin'])][:120],['Assessment Evidence','Value'])
    _section(doc,'9.2 REPAYMENT SCHEDULE',2)
    doc.add_paragraph(f"Proposed repayment: {_fmt(state.get('repayment'))}; tenure: {_fmt(state.get('tenure'))}. Exact repayment schedule is subject to sanction terms and verified facility structure.")

    _section(doc,'10. REGULATORY / POLICY COMPLIANCE',1)
    checks=state.get('policy_checks',[])
    _table(doc,[[c.get('rule'),c.get('status'),c.get('reason')] for c in checks],['Policy / Rule','Status','Evidence / Reason']) if checks else doc.add_paragraph('No policy rules have been configured for this application.')
    _section(doc,'10.1 DUE DILIGENCE / ROC / FRAUD / KYC',2)
    _table(doc,[[k,_fmt(v)] for k,v in fields.items() if any(x in k.lower() for x in ['kyc','pan','aadhaar','gst','roc','fraud','rbi','sebi','ecgc','insurance','due_diligence'])][:160],['Due Diligence Item','Value'])

    _section(doc,'11. PEER / MARKET BENCHMARKING',1)
    doc.add_paragraph(state.get('ai_narratives',{}).get('benchmarking') or 'Peer benchmarking is limited to information available in the uploaded documents and configured external sources. Missing market data is not fabricated.')
    _table(doc,[[k,_fmt(v)] for k,v in fields.items() if any(x in k.lower() for x in ['benchmark','peer','industry','market','rating'])][:100],['Benchmark Evidence','Value'])

    _section(doc,'12. RECOMMENDATION',1)
    doc.add_paragraph(state.get('ai_narratives',{}).get('recommendation') or 'Recommendation is subject to credit officer review and applicable sanctioning authority.')
    _section(doc,'12.1 CONDITIONS PRECEDENT / MONITORING',2)
    conditions=['Verify originals / digitally signed source documents before sanction or disbursement.','Validate MCA/CIN data fetched through FileSure against source records.','Confirm all mandatory KYC, collateral, insurance and legal due-diligence requirements.','Confirm policy exceptions and concessions, if any, through the competent authority.','Credit officer to validate all extracted figures before final sanction.']
    for c in conditions: doc.add_paragraph(c,style='List Bullet')

    _section(doc,'ANNEXURE A — FINANCIAL EVIDENCE',1)
    for d in documents:
        doc.add_page_break(); doc.add_heading(d.get('original_filename','Document'),2)
        doc.add_paragraph('Document type: '+_fmt(d.get('display_name')))
        doc.add_paragraph('Extraction method: '+_fmt(d.get('extraction_method')))
        fields_d=d.get('extracted_fields') or {}
        _table(doc,[[k,_fmt(v)] for k,v in fields_d.items()],['Extracted Field','Value'])
    _section(doc,'ANNEXURE B — EVIDENCE AND AUDIT TRAIL',1)
    doc.add_paragraph('This CAM records source-derived information separately from AI-generated narrative. AI narrative does not override deterministic calculations or mandatory policy results.')
    _table(doc,[['Document count',len(documents)],['MCA status',(state.get('mca') or {}).get('status')],['MCA CIN',(state.get('mca') or {}).get('cin')],['AI model',os.getenv('GROQ_MODEL','openai/gpt-oss-120b')],['Generated UTC',datetime_now()]],['Audit Item','Value'])
    _section(doc,'HUMAN CREDIT OFFICER REVIEW',1)
    doc.add_paragraph('Final credit decision, approval, policy override and sanction remain under authorized human control.')
    return doc

def datetime_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime('%d-%b-%Y %H:%M UTC')

def generate_cam(session_id):
    state=get_cam(session_id)
    if not state: raise ValueError('CAM session not found')

    # Generation must use the same readiness source-of-truth as the Final Review
    # and Generate CAM screens.  Do not gate on state['status'] alone: Point 9
    # and the newer stage-based workflow can be fully complete while an older
    # session-level status still says 'in_analysis'.
    from app.cam.policy_engine import readiness as _policy_readiness
    policy_gate = _policy_readiness(state)

    if not policy_gate.get('cam_analysis_complete'):
        missing = policy_gate.get('missing_cam_sections') or []
        if missing:
            labels = ', '.join(f"{item.get('number')} {item.get('title')}" for item in missing)
            raise ValueError(f'Complete CAM analysis before generating the CAM. Pending: {labels}')
        raise ValueError('Complete CAM analysis before generating the CAM')

    if not policy_gate.get('analysis_complete'):
        raise ValueError(policy_gate.get('message') or 'Active policy has changed or policy analysis is stale. Re-run CAM vs Policy Analysis before generating the final CAM')

    # policy_review_completed is retained for backward compatibility/audit, but
    # readiness.analysis_complete is the authoritative generation gate because
    # it also proves the policy hash and CAM snapshot are current.
    if not state.get('policy_review_completed') and not policy_gate.get('analysis_complete'):
        raise ValueError('Complete CAM vs Policy review before generating the final CAM')
    db,row=get_db_application(session_id)
    if not row:
        if db: db.close()
        raise ValueError('Application not found')
    documents=[document_payload(d,include_text=True) for d in row.documents]
    db.close()
    output_docx=OUTPUT_DIR/f"{state['cam_id']}.docx"
    normalized = state.get('normalized_cam_data') or build_normalized_cam_data(state, documents)
    state['normalized_cam_data'] = normalized
    state['verification_bundle'] = normalized.get('verification')
    save_cam(state)
    doc=build_twenty_page_cam(state, documents, normalized)
    doc.save(str(output_docx))
    pdf_path=OUTPUT_DIR/f"{state['cam_id']}.pdf"
    pdf_created=False
    soffice=shutil.which('soffice')
    if soffice:
        try:
            subprocess.run([soffice,'--headless','--convert-to','pdf','--outdir',str(OUTPUT_DIR),str(output_docx)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
            pdf_created=pdf_path.exists()
        except Exception: pass
    state=get_cam(session_id); state['docx_path']=str(output_docx); state['pdf_path']=str(pdf_path) if pdf_created else None; state['status']='completed'; state['current_step']='CAM generated successfully'; save_cam(state)


