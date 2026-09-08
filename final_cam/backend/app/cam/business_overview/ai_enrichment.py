import json
from typing import Any, Dict

from app.cam.llm_gateway import LLMGatewayError, chat
from app.config import get_groq_api_key, get_groq_model


def build_ai_business_overview(context: Dict[str, Any]) -> Dict[str, Any]:
    status = {
        "configured": bool(get_groq_api_key()),
        "model": get_groq_model(),
        "status": "not_configured",
        "error": None,
    }
    if not status["configured"]:
        status["error"] = "GROQ_API_KEY is not configured."
        return {"text": None, "source": "not_generated", "llm_status": status}

    compact = {
        "business_model": context.get("business_model"),
        "products_services": context.get("products_services"),
        "customer_profile": context.get("customer_profile"),
        "supplier_profile": context.get("supplier_profile"),
        "operating_footprint": context.get("operating_footprint"),
        "company_structure": context.get("company_structure"),
        "revenue_profile": context.get("revenue_profile"),
        "market_position": context.get("market_position"),
        "strengths": context.get("strengths"),
        "business_risks": context.get("business_risks"),
        "recent_developments": context.get("recent_developments"),
    }
    system = (
        "You are a controlled bank CAM Business Overview drafting assistant. Use ONLY the supplied structured evidence. "
        "Do not invent customers, market share, products, locations, capacity, contracts, financial values, or competitive claims. "
        "Do not perform new financial calculations. Write a concise 150-220 word professional Business Overview covering the business model, "
        "products/services where available, customer profile, operating footprint, revenue profile and trend, market position, recent developments, "
        "and key business strengths/risks. Clearly state when important information is unavailable. Do not recommend sanction, approval or rejection."
    )
    prompt = "BUSINESS_OVERVIEW_CONTEXT:\n" + json.dumps(compact, ensure_ascii=False, default=str)
    try:
        text = chat([
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ], temperature=0.1).strip()
        if not text:
            status.update({"status": "empty_response", "error": "Groq returned an empty Business Overview."})
            return {"text": None, "source": "not_generated", "llm_status": status}
        status["status"] = "success"
        return {"text": text, "source": "ai_generated", "llm_status": status}
    except LLMGatewayError as exc:
        status.update({"status": "provider_error", "error": str(exc), "status_code": getattr(exc, "status_code", None)})
    except Exception as exc:
        status.update({"status": "unexpected_error", "error": f"{type(exc).__name__}: {exc}"})
    return {"text": None, "source": "not_generated", "llm_status": status}
