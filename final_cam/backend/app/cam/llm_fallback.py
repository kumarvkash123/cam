"""
LLM fallback classifier -- only called when rule-based scoring lands below
the `needs_review` threshold (i.e. rules genuinely couldn't decide).

Important: results from this module are NEVER auto-accepted. They always
come back tagged as needing user confirmation, regardless of how confident
the LLM sounds. This keeps the system auditable for sensitive KYC/financial
documents.

Uses Anthropic's API. Set ANTHROPIC_API_KEY in the environment.
"""

import os
import json
from typing import List

_client = None


def _get_client():
    """
    Lazy-initialized so importing this module (and therefore app.py) never
    requires anthropic to be configured or even installed correctly, unless
    a document actually falls through to the LLM fallback path. This also
    means v1 (born-digital PDFs only, high rule-based confidence) can run
    with zero Anthropic setup at all.
    """
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def llm_classify(text: str, candidate_doc_types: List[dict]) -> dict:
    """
    candidate_doc_types: the top-N candidates from the rule engine (with low
    scores) -- we constrain the LLM to choose among plausible options rather
    than doing open-ended classification, which is far more reliable.
    """
    options = [c["display_name"] for c in candidate_doc_types]
    options_str = "\n".join(f"- {o}" for o in options)

    prompt = f"""You are classifying a scanned Indian KYC/loan document based on its OCR-extracted text.
The rule-based classifier could not confidently decide between these candidates:

{options_str}

Extracted text (may contain OCR noise):
---
{text[:3000]}
---

Respond ONLY with JSON in this exact format, nothing else:
{{"doc_type": "<one of the candidate names above, or 'unclear'>", "reasoning": "<one short sentence>"}}
"""

    client = _get_client()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()

    try:
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = {"doc_type": "unclear", "reasoning": "LLM response could not be parsed"}

    parsed["needs_user_confirmation"] = True  # always -- see module docstring
    return parsed
