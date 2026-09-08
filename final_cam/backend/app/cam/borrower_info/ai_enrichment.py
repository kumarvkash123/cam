import json
from typing import Any, Dict
from app.cam.llm_gateway import chat, LLMGatewayError
from app.config import get_groq_api_key, get_groq_model


def build_ai_overview(profile: Dict[str, Any]) -> Dict[str, Any]:
    status = {"configured": bool(get_groq_api_key()), "model": get_groq_model(), "status": "not_configured", "error": None}
    if not status["configured"]:
        status["error"] = "GROQ_API_KEY is not configured."
        return {"text": None, "source": "not_generated", "llm_status": status}

    compact = {
        "corporate_profile": profile.get("corporate_profile"),
        "registration": profile.get("registration"),
        "promoters_directors": profile.get("promoters_directors"),
        "ownership": profile.get("ownership"),
        "business_profile": profile.get("business_profile"),
        "geography": profile.get("geography"),
        "bank_relationship": profile.get("bank_relationship"),
        "public_information": profile.get("public_information"),
        "source_conflicts": profile.get("source_conflicts"),
    }
    system = (
        "You are a bank CAM borrower-information writing assistant. Use only the supplied structured evidence. "
        "Do not invent identifiers, ownership percentages, locations, management names, financial values or verification outcomes. "
        "Write a concise 120-180 word borrower overview covering corporate identity and vintage, line of business, management/ownership "
        "where available, operating geography, bank relationship, and material public observations. Clearly state when important information "
        "is unavailable or under review. Do not recommend sanction/approval/rejection."
    )
    prompt = "BORROWER EVIDENCE:\n" + json.dumps(compact, ensure_ascii=False, default=str)
    try:
        text = chat([{"role": "system", "content": system}, {"role": "user", "content": prompt}], temperature=0.1).strip()
        if not text:
            status.update({"status": "empty_response", "error": "Groq returned an empty Borrower Overview."})
            return {"text": None, "source": "not_generated", "llm_status": status}
        status["status"] = "success"
        return {"text": text, "source": "ai_generated", "llm_status": status}
    except LLMGatewayError as exc:
        status.update({"status": "provider_error", "error": str(exc), "status_code": exc.status_code})
    except Exception as exc:
        status.update({"status": "unexpected_error", "error": f"{type(exc).__name__}: {exc}"})
    return {"text": None, "source": "not_generated", "llm_status": status}
