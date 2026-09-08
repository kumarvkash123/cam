import re
from typing import Any, Dict, List

from app.cam.llm_gateway import LLMGatewayError, chat
from app.cam.response_formatter import format_assistant_response


def _chunks_from_sources(sources: List[Dict[str, Any]], max_chars: int = 1800) -> List[Dict[str, Any]]:
    chunks = []
    for src in sources or []:
        filename = src.get("filename") or src.get("original_filename") or "Unknown document"
        doc_type = src.get("doc_type") or src.get("category") or "Document"
        pages = src.get("pages") or []
        if pages:
            for p in pages:
                text = (p.get("text") or "").strip()
                if not text:
                    continue
                page_no = p.get("page_no") or p.get("page") or 1
                for i in range(0, len(text), max_chars):
                    chunks.append({"id": f"{len(chunks)+1}", "filename": filename, "doc_type": doc_type, "page": page_no, "text": text[i:i + max_chars]})
        else:
            text = (src.get("text") or src.get("extracted_text") or "").strip()
            if text:
                for i in range(0, len(text), max_chars):
                    chunks.append({"id": f"{len(chunks)+1}", "filename": filename, "doc_type": doc_type, "page": None, "text": text[i:i + max_chars]})
    return chunks


def _terms(q: str) -> List[str]:
    stop = {"what", "where", "when", "which", "with", "from", "does", "this", "that", "the", "and", "for", "are", "how"}
    return [x for x in re.findall(r"[a-zA-Z0-9]{3,}", q.lower()) if x not in stop]


def retrieve(sources: List[Dict[str, Any]], query: str, top_k: int = 6) -> List[Dict[str, Any]]:
    chunks = _chunks_from_sources(sources)
    if not chunks:
        return []
    terms = _terms(query)
    qlower = query.lower()
    scored = []
    for c in chunks:
        text = c["text"].lower()
        score = sum(text.count(t) for t in terms)
        if qlower in text:
            score += 8
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [c for score, c in scored if score > 0][:top_k]
    return selected or chunks[:top_k]


def _call_groq(question: str, context: List[Dict[str, Any]], history: List[Dict[str, str]]) -> str:
    evidence = []
    for c in context:
        label = f"[S{c['id']}] {c['filename']}"
        if c.get("page") is not None:
            label += f" — Page {c['page']}"
        evidence.append({"source": label, "text": c["text"]})

    prompt = (
        "You are a controlled bank document/policy assistant. Answer ONLY from the supplied source excerpts. "
        "If the answer is not supported, say that it is not available in the uploaded documents. "
        "Do not invent policy limits, financial figures, dates, names or conclusions. "
        "Cite supporting sources inline using [S<number>] exactly as supplied. "
        "For policy questions, explain the applicable rule and condition. For borrower-document questions, summarize the evidence.\n\n"
        f"QUESTION:\n{question}\n\nSOURCES:\n"
    )
    # Keep the retrieved context itself small; the gateway separately limits
    # conversation history and total message size.
    source_text = "\n".join(f"{x['source']}: {x['text']}" for x in evidence)
    prompt += source_text[:12000]

    messages = [{"role": "system", "content": "You are a source-grounded bank RAG assistant."}]
    for h in (history or [])[-6:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": prompt})

    try:
        return format_assistant_response(chat(messages, temperature=0.1))
    except LLMGatewayError as exc:
        return str(exc)


def answer_question(question: str, sources: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    context = retrieve(sources, question)
    answer = _call_groq(question, context, history or [])
    citations = []
    seen = set()
    for c in context:
        key = (c["filename"], c.get("page"))
        if key in seen:
            continue
        seen.add(key)
        citations.append({"source_id": f"S{c['id']}", "filename": c["filename"], "page": c.get("page"), "doc_type": c.get("doc_type")})
    return {"answer": answer, "citations": citations}
