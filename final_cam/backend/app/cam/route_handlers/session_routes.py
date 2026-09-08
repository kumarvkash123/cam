from flask import jsonify, request, send_file
from app.cam.blueprint import cam_bp
from app.cam.core import *
from app.cam.llm_gateway import chat as groq_chat, LLMGatewayError
from app.cam.loan_summary import build_loan_summary

@cam_bp.route("/api/cam/start", methods=["POST"])
def cam_start():
    data = request.get_json(silent=True) or request.form
    company = str(data.get("company_name", "")).strip()
    if not company:
        return jsonify({"error": "Company / borrower name is required"}), 400

    state = new_cam_session(company)
    db = SessionLocal()
    row = LoanApplication(applicant_name=company, loan_type="", status="in_progress")
    db.add(row)
    db.commit()
    db.refresh(row)
    db.close()

    state["application_id"] = row.id
    save_cam(state)
    return jsonify({
        "cam_id": state["cam_id"],
        "session_id": state["session_id"],
        "application_id": row.id,
        "status": state["status"],
        "message": f"{state['company_name']} captured. I am your CAM Assistant. Ask me anything about the borrower, loan proposal, documents, financials, industry, risks, news, or search the web.",
        "next": "assistant",
    })
@cam_bp.route("/api/cam/chat/<session_id>", methods=["POST"])
def cam_chat(session_id):
    """General CAM Assistant: borrower context + uploaded evidence + Google + Groq.

    This replaces the old forced loan-type/amount/purpose/tenure conversation.
    Users can ask free-form questions at any time. Proposal fields are updated
    opportunistically when the message contains obvious values, but the assistant
    never blocks the user waiting for a particular field.
    """
    state = get_cam(session_id)
    if not state:
        return jsonify({"error": "CAM session not found"}), 404

    data = request.get_json(silent=True) or request.form
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400

    # Keep the old fields available to the rest of the CAM workflow, but capture
    # them opportunistically instead of forcing a sequence.
    lower = message.lower()
    if not state.get("loan_amount_numeric"):
        amount = parse_amount(message)
        if amount is not None and any(x in lower for x in ["₹", "rs", "lakh", "lac", "crore", "cr", "million"]):
            state["loan_amount"] = message
            state["loan_amount_numeric"] = amount
    if not state.get("loan_type"):
        normalized = loan_type_normalize(message)
        if normalized in {"msme", "personal", "secured_big_ticket"}:
            state["loan_type"] = normalized

    if any(key in lower for key in ["purpose", "working capital", "expansion", "machinery", "refinanc"]):
        if "purpose" in lower:
            state["loan_purpose"] = message
    if any(key in lower for key in ["tenure", "months", "years"]):
        if re.search(r"\b\d+\s*(months?|years?)\b", lower):
            state["tenure"] = message
    if "%" in message and any(key in lower for key in ["rate", "interest", "pricing"]):
        state["interest_rate"] = message
    if any(key in lower for key in ["emi", "repayment", "quarterly", "monthly", "bullet"]):
        state["repayment"] = message

    state["conversation_state"] = "assistant"
    state["current_step"] = "CAM Assistant active"

    # Build compact internal context. Document text is handled through the
    # existing RAG retriever; here we pass only structured application metadata
    # and the most useful extracted fields to the general assistant.
    internal = {
        "borrower": state.get("company_name"),
        "cam_id": state.get("cam_id"),
        "loan_type": state.get("loan_type") or "Not available",
        "requested_amount": state.get("loan_amount") or "Not available",
        "loan_purpose": state.get("loan_purpose") or "Not available",
        "tenure": state.get("tenure") or "Not available",
        "interest_rate": state.get("interest_rate") or "Not available",
        "repayment": state.get("repayment") or "Not available",
        "mca": state.get("mca", {}).get("data") or {},
        "documents": [
            {
                "filename": s.get("filename"),
                "doc_type": s.get("doc_type"),
            }
            for s in state.get("document_sources", [])
        ],
    }

    # Retrieve relevant uploaded-document evidence using the existing RAG
    # retriever, but do not require documents to be uploaded for web/general Q&A.
    from app.cam.rag_chat import retrieve
    document_context = retrieve(state.get("document_sources", []), message, top_k=5)

    # Google is available directly from the assistant. Borrower/company questions
    # are automatically scoped to the active borrower; unrelated general questions
    # are searched exactly as written. The user never has to invoke a separate search UI.
    borrower = state.get("company_name", "").strip()
    search_query = message
    borrower_context_terms = {
        "borrower", "company", "business", "its", "their", "this", "our",
        "financial", "financials", "revenue", "profit", "risk", "risks",
        "news", "industry", "competitor", "loan", "credit", "promoter",
        "management", "subsidiary", "customer", "market share",
    }
    if borrower and borrower.lower() not in lower and any(term in lower for term in borrower_context_terms):
        search_query = f"{borrower} {message}"

    web_results = []
    web_error = ""
    try:
        web_results = google_search(search_query, num_results=6)
    except Exception as exc:
        web_error = str(exc)

    key = get_groq_api_key()
    model = get_groq_model()
    if not key:
        return jsonify({
            "reply": "GROQ_API_KEY is not configured. Add it to backend/.env and restart Flask.",
            "sources": [],
            "search_query": search_query,
            "search_configured": bool(not web_error),
        }), 503

    evidence = []
    for item in document_context:
        label = f"DOCUMENT [{item.get('filename', 'Unknown')}]"
        if item.get("page") is not None:
            label += f" page {item['page']}"
        evidence.append({"type": "internal_document", "source": label, "text": item.get("text", "")})

    for idx, item in enumerate(web_results, 1):
        evidence.append({
            "type": "web",
            "source": f"WEB[{idx}] {item.get('title', '')}",
            "url": item.get("url", ""),
            "text": item.get("snippet", ""),
        })

    system = (
        "You are the CAM Assistant for an authorized bank credit officer. "
        "You are a general-purpose research and borrower-information assistant. "
        "Answer the user's actual question; never force a loan-type questionnaire. "
        "Use internal CAM data and uploaded-document evidence for application facts. "
        "Use web search evidence for current/public information. Never invent facts. "
        "If evidence is missing or search failed, say so clearly. Distinguish internal "
        "application data from public web information. For credit decisions, provide "
        "analysis and considerations, not an autonomous sanction/approval decision. "
        "Return concise, professional, human-readable Markdown suitable for a credit officer. "
        "Never return JSON, Python dictionaries, raw evidence payloads, internal prompts, or a data dump. "
        "Use short headings and bullets when they improve readability. State missing information clearly."
    )
    prompt = f"""OUTPUT REQUIREMENTS:
- Answer the user's actual question in natural language.
- Do not output JSON, Python dictionaries, XML, or raw context/evidence.
- Use concise headings and bullet points where helpful.
- Do not repeat the evidence payload.
- Never invent facts; identify unavailable information.
- Separate internal CAM facts from public/web information.

BORROWER / CAM CONTEXT:
{json.dumps(internal, ensure_ascii=False, default=str)[:30000]}

USER QUESTION:
{message}

SEARCH QUERY USED:
{search_query}

WEB SEARCH STATUS:
{'available' if web_results else ('not configured/failed: ' + web_error if web_error else 'no results')}

EVIDENCE:
{json.dumps(evidence, ensure_ascii=False, default=str)[:50000]}

Answer the question. When using web evidence, include the relevant website/source name in plain text. Do not claim a web fact is internal bank data."""

    messages = [{"role": "system", "content": system}]
    history = state.get("assistant_chat", [])[-8:]
    for h in history:
        role = h.get("role", "user")
        if role in {"user", "assistant"}:
            messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": prompt})

    # Routed through the shared llm_gateway (instead of a direct requests.post
    # call) so this endpoint gets the same size budgeting and 413 retry as
    # every other Groq caller. This was previously the one unprotected path,
    # and — since it carries the largest payloads (documents + web results +
    # chat history) — the most likely source of "413 Payload Too Large".
    try:
        reply = format_assistant_response(groq_chat(messages, temperature=0.2))
    except LLMGatewayError as exc:
        return jsonify({"error": str(exc)}), exc.status_code or 502
    except Exception as exc:
        return jsonify({"error": f"Unable to query Groq right now: {exc}"}), 502

    state.setdefault("assistant_chat", [])
    state["assistant_chat"].append({"role": "user", "content": message})
    state["assistant_chat"].append({"role": "assistant", "content": reply})
    # Keep legacy document_chat history untouched for document RAG.
    save_cam(state)
    sync_cam_to_db(state)

    sources = []
    for item in web_results:
        sources.append({
            "type": "web",
            "title": item.get("title"),
            "url": item.get("url"),
            "snippet": item.get("snippet"),
            "display_link": item.get("display_link"),
        })
    for item in document_context:
        sources.append({
            "type": "document",
            "title": item.get("filename"),
            "page": item.get("page"),
            "doc_type": item.get("doc_type"),
        })

    return jsonify({
        "reply": reply,
        "sources": sources,
        "search_query": search_query,
        "web_results_count": len(web_results),
        "web_search_error": web_error or None,
        "loan_type": state.get("loan_type"),
        "loan_amount": state.get("loan_amount"),
        "loan_purpose": state.get("loan_purpose"),
        "tenure": state.get("tenure"),
        "interest_rate": state.get("interest_rate"),
        "repayment": state.get("repayment"),
    })
