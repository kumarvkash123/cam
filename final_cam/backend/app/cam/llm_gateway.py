"""Centralized, size-aware Groq client for all LLM calls.

The gateway prevents oversized requests from reaching the provider by applying
an input budget to the complete message list (system prompt + history + user
context). It also performs one controlled retry with a smaller payload when a
provider returns HTTP 413.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from app.config import get_groq_api_key, get_groq_model

LOGGER = logging.getLogger(__name__)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Character budgets are deliberately conservative. Roughly 4 chars/token is a
# useful estimate for English prose; the real provider tokenizer can vary.
MAX_REQUEST_CHARS = 24000
MAX_HISTORY_CHARS = 6000
MAX_MESSAGE_CHARS = 18000
RETRY_REQUEST_CHARS = 12000
TIMEOUT_SECONDS = 90
EMPTY_RESPONSE_RETRY_CHARS = 10000
MAX_COMPLETION_TOKENS = 1400


def _is_gpt_oss(model: str) -> bool:
    return str(model or "").startswith("openai/gpt-oss-")


class LLMGatewayError(RuntimeError):
    """Safe, user-facing LLM error."""

    def __init__(self, message: str, *, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return str(content)


def _trim(text: str, max_chars: int) -> str:
    text = text or ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[Context truncated by LLM gateway]"


def _prepare_messages(messages: List[Dict[str, Any]], budget: int) -> List[Dict[str, str]]:
    """Keep system prompt, current request, and most recent history in budget."""
    if not messages:
        return []

    normalized = []
    for m in messages:
        role = str(m.get("role") or "user")
        content = _content_to_text(m.get("content"))
        normalized.append({"role": role, "content": content})

    # Preserve system message and the final user message. Compress middle
    # history first because it is conversational context, not source evidence.
    system = normalized[0] if normalized[0]["role"] == "system" else None
    body = normalized[1:] if system else normalized[:]
    current = body[-1] if body else None
    history = body[:-1] if current else []

    out: List[Dict[str, str]] = []
    used = 0
    if system:
        system_content = _trim(system["content"], min(3000, budget))
        out.append({"role": "system", "content": system_content})
        used += len(system_content)

    # Keep the newest history items, bounded independently.
    history_text_used = 0
    selected_history = []
    for item in reversed(history):
        content = _trim(item["content"], MAX_MESSAGE_CHARS)
        if history_text_used + len(content) > MAX_HISTORY_CHARS:
            remaining = MAX_HISTORY_CHARS - history_text_used
            if remaining <= 0:
                break
            content = _trim(content, remaining)
        if not content:
            continue
        selected_history.append({"role": item["role"], "content": content})
        history_text_used += len(content)
        if history_text_used >= MAX_HISTORY_CHARS:
            break
    selected_history.reverse()

    for item in selected_history:
        if used + len(item["content"]) > budget:
            break
        out.append(item)
        used += len(item["content"])

    if current:
        remaining = max(1000, budget - used)
        out.append({"role": current["role"], "content": _trim(current["content"], remaining)})

    return out


def _post(messages: List[Dict[str, str]], *, temperature: float = 0.1,
          response_format: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    key = get_groq_api_key()
    if not key:
        raise LLMGatewayError("GROQ_API_KEY is not configured.")

    model = get_groq_model()
    payload: Dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
    }
    # GPT-OSS returns reasoning separately by default on Groq. Loan-summary and
    # CAM calls need only the final answer, so exclude reasoning explicitly.
    # This also prevents reasoning tokens from obscuring an otherwise valid
    # final response.
    if _is_gpt_oss(model):
        payload["include_reasoning"] = False
        payload["reasoning_effort"] = "low"
    if response_format:
        payload["response_format"] = response_format

    LOGGER.info(
        "[GROQ-RAW-DEBUG] request model=%s messages=%s chars=%s include_reasoning=%s reasoning_effort=%s response_format=%s",
        model, len(messages), sum(len(m.get("content") or "") for m in messages),
        payload.get("include_reasoning"), payload.get("reasoning_effort"),
        (response_format or {}).get("type") if response_format else "text",
    )

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or [] if isinstance(data, dict) else []
        choice = choices[0] if choices else {}
        message = choice.get("message") or {} if isinstance(choice, dict) else {}
        content = message.get("content") if isinstance(message, dict) else None
        reasoning = message.get("reasoning") if isinstance(message, dict) else None
        LOGGER.info(
            "[GROQ-RAW-DEBUG] response status=%s finish_reason=%s content_length=%s reasoning_present=%s message_keys=%s usage=%s",
            response.status_code,
            choice.get("finish_reason") if isinstance(choice, dict) else None,
            len(content) if isinstance(content, str) else 0,
            bool(reasoning),
            sorted(message.keys()) if isinstance(message, dict) else [],
            data.get("usage") if isinstance(data, dict) else None,
        )
        return data
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status == 413:
            raise LLMGatewayError("LLM request payload exceeded the provider limit.", status_code=413) from exc
        if status == 429:
            raise LLMGatewayError("LLM provider rate limit reached. Please retry shortly.", status_code=429) from exc
        detail = ""
        try:
            detail = (exc.response.text or "")[:500]
        except Exception:
            pass
        LOGGER.exception("Groq HTTP error status=%s detail=%s", status, detail)
        raise LLMGatewayError("The LLM provider returned an error.", status_code=status) from exc
    except requests.RequestException as exc:
        LOGGER.exception("Groq network error")
        raise LLMGatewayError("Unable to reach the LLM provider.") from exc
    except ValueError as exc:
        LOGGER.exception("Invalid Groq JSON response")
        raise LLMGatewayError("The LLM provider returned an invalid response.") from exc


def chat(messages: List[Dict[str, Any]], *, temperature: float = 0.1,
         response_format: Optional[Dict[str, Any]] = None) -> str:
    """Call Groq with a hard request budget and one 413 recovery attempt."""
    prepared = _prepare_messages(messages, MAX_REQUEST_CHARS)
    total_chars = sum(len(m["content"]) for m in prepared)
    LOGGER.info("LLM request model=%s chars=%s messages=%s", get_groq_model(), total_chars, len(prepared))

    try:
        data = _post(prepared, temperature=temperature, response_format=response_format)
    except LLMGatewayError as exc:
        if exc.status_code != 413:
            raise
        # Second attempt: aggressively shrink history and current context.
        retry_messages = _prepare_messages(messages, RETRY_REQUEST_CHARS)
        LOGGER.warning("Groq returned 413; retrying with chars=%s", sum(len(m["content"]) for m in retry_messages))
        try:
            data = _post(retry_messages, temperature=temperature, response_format=response_format)
        except LLMGatewayError as retry_exc:
            if retry_exc.status_code == 413:
                raise LLMGatewayError(
                    "The AI request is still too large after reducing document context. "
                    "Please ask a more focused question or use a smaller document scope.",
                    status_code=413,
                ) from retry_exc
            raise

    def _extract_final_text(payload: Dict[str, Any]) -> str:
        try:
            choice = payload["choices"][0]
            message = choice["message"] or {}
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMGatewayError("The LLM provider returned an unexpected response.") from exc
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        return ""

    content = _extract_final_text(data)
    if content:
        return content

    # HTTP 200 with blank assistant content is different from rate limiting.
    # Retry once with a smaller context and an explicit final-answer reminder.
    retry_messages = _prepare_messages(messages, EMPTY_RESPONSE_RETRY_CHARS)
    if retry_messages:
        retry_messages = [dict(m) for m in retry_messages]
        last = retry_messages[-1]
        if last.get("role") == "user":
            last["content"] = _trim(
                (last.get("content") or "")
                + "\n\nIMPORTANT: Return the final answer as non-empty plain text. Do not return reasoning only.",
                MAX_MESSAGE_CHARS,
            )
    LOGGER.warning(
        "[GROQ-RAW-DEBUG] empty_content_retry model=%s chars=%s",
        get_groq_model(), sum(len(m.get("content") or "") for m in retry_messages),
    )
    retry_data = _post(retry_messages, temperature=temperature, response_format=response_format)
    content = _extract_final_text(retry_data)
    if content:
        LOGGER.info("[GROQ-RAW-DEBUG] empty_content_retry_success content_length=%s", len(content))
        return content

    try:
        choice = (retry_data.get("choices") or [{}])[0]
        finish_reason = choice.get("finish_reason")
        message = choice.get("message") or {}
        reasoning_present = bool(message.get("reasoning"))
    except Exception:
        finish_reason = None
        reasoning_present = False
    raise LLMGatewayError(
        "Groq completed the request but returned no final answer after one controlled retry "
        f"(finish_reason={finish_reason}, reasoning_present={reasoning_present})."
    )


def generate_json(messages: List[Dict[str, Any]], *, temperature: float = 0.1) -> Dict[str, Any]:
    import json

    content = chat(
        messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMGatewayError("The LLM returned invalid JSON.") from exc
    if not isinstance(data, dict):
        raise LLMGatewayError("The LLM returned an invalid JSON object.")
    return data
