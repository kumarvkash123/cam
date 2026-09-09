import json
import logging
from typing import Any, Dict

from app.cam.llm_gateway import LLMGatewayError, chat, generate_json

LOGGER = logging.getLogger(__name__)


def _bounded_text(value: Any, limit: int = 3000) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[:limit] + " [truncated]"


def _bounded_evidence(state, documents):
    """Build CAM evidence without serializing entire source documents."""
    loan = {
        k: state.get(k)
        for k in ["company_name", "loan_type", "loan_amount", "loan_purpose", "tenure", "interest_rate", "repayment"]
    }
    doc_items = []
    for d in documents or []:
        fields = d.get("extracted_fields") or {}
        safe_fields = {str(k): _bounded_text(v, 1200) for k, v in fields.items()}
        doc_items.append({
            "file": _bounded_text(d.get("original_filename"), 300),
            "type": _bounded_text(d.get("doc_type"), 100),
            "fields": safe_fields,
        })

    policy_items = []
    for p in (state.get("policy_sources") or []):
        pages = []
        for page in (p.get("pages") or [])[:8]:
            pages.append({
                "page": page.get("page_no") or page.get("page") or 1,
                "text": _bounded_text(page.get("text"), 1800),
            })
        policy_items.append({"file": _bounded_text(p.get("filename"), 300), "pages": pages})

    return {
        "loan": loan,
        "mca": state.get("mca", {}).get("data"),
        "documents": doc_items,
        "policy_sources": policy_items,
    }


def generate_cam_narratives(state, documents, reports):
    evidence = _bounded_evidence(state, documents)
    prompt = (
        "You are a bank credit appraisal writer. Write concise, professional CAM narrative from ONLY the supplied evidence. "
        "Never invent figures, names, dates, ratings, collateral values or compliance results. "
        'If a fact is missing say "Not available from submitted evidence". '
        "Do not make a final credit decision and do not override deterministic policy/calculation results. "
        "Return JSON with keys executive_summary,business_overview,conduct,cash_flow,assessment,benchmarking,recommendation.\n\n"
        f"EVIDENCE:\n{json.dumps(evidence, ensure_ascii=False, default=str)}"
    )
    messages = [
        {"role": "system", "content": "You are a controlled bank CAM drafting service."},
        {"role": "user", "content": prompt},
    ]
    try:
        return generate_json(messages, temperature=0.1)
    except LLMGatewayError as exc:
        LOGGER.warning("CAM narrative generation skipped: %s", exc)
        return {}


def generate_loan_summary_narrative(summary_evidence: Dict[str, Any]) -> str:
    """Narrate only the bounded, normalized Loan Summary context."""
    prompt = (
        "You are assisting a bank credit officer in drafting the Loan Summary section of a Credit Appraisal Memo. "
        "Use ONLY the structured facts supplied below. Do not invent missing information. Do not perform new financial "
        "calculations and do not recommend sanction, rejection, approval, or decline. Write 90-130 words in 3-5 concise sentences in plain, "
        "professional language covering: borrower/business profile; requested facility, amount and purpose; key financial "
        "performance and ratios; credit/repayment conduct; major risks and mitigants; collateral/security position; and only "
        "material compliance or public-information observations. Public-search content is supporting evidence and must be "
        "described cautiously. If an important group is unavailable, state that it is not available from current evidence. "
        "Prioritize the overall credit picture; do not repeat every field already shown in the UI. Return plain text only, no headings, JSON or markdown.\n\n"
        f"LOAN_SUMMARY_CONTEXT:\n{json.dumps(summary_evidence, ensure_ascii=False, default=str)}"
    )
    messages = [
        {"role": "system", "content": "You are a controlled bank CAM drafting service. You narrate supplied evidence; deterministic calculations and human credit decisions remain authoritative."},
        {"role": "user", "content": prompt},
    ]
    return chat(messages, temperature=0.1).strip()
