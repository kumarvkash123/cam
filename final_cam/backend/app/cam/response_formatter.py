"""Normalize LLM output into safe, human-readable CAM assistant text."""
import json
import re
from typing import Any


def _json_to_markdown(value: Any, level: int = 0) -> str:
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            label = str(key).replace("_", " ").strip().title()
            if isinstance(item, (dict, list)):
                parts.append(f"**{label}**\n{_json_to_markdown(item, level + 1)}")
            else:
                parts.append(f"• **{label}:** {item}")
        return "\n".join(parts)
    if isinstance(value, list):
        return "\n".join(f"• {(_json_to_markdown(item, level + 1) if isinstance(item, (dict, list)) else item)}" for item in value)
    return str(value)


def format_assistant_response(text: str) -> str:
    """Convert accidental JSON/data dumps into readable Markdown without inventing content."""
    raw = str(text or "").strip()
    if not raw:
        return "I could not generate a response from the available evidence."

    candidate = raw.strip("` \n")
    if (candidate.startswith("{") and candidate.endswith("}")) or (candidate.startswith("[") and candidate.endswith("]")):
        try:
            parsed = json.loads(candidate)
            return _json_to_markdown(parsed)
        except Exception:
            pass

    # Remove fenced markdown wrappers but preserve useful markdown inside them.
    raw = re.sub(r"^```(?:markdown|md|text)?\s*", "", raw, flags=re.I)
    raw = re.sub(r"\s*```$", "", raw)
    # Convert common raw key/value dumps into bullets.
    lines = []
    for line in raw.splitlines():
        s = line.strip()
        if re.match(r'^["\']?[A-Za-z][A-Za-z0-9 _-]{1,50}["\']?\s*:\s*', s) and not s.startswith(("http://", "https://")):
            s = re.sub(r'^["\']?([A-Za-z][A-Za-z0-9 _-]{1,50})["\']?\s*:\s*', lambda m: f"• **{m.group(1).replace('_',' ').title()}:** ", s, count=1)
        lines.append(s)
    rendered = "\n".join(lines).strip()

    # Long single-paragraph assistant answers are difficult to scan in CAM.
    # Convert them into sentence bullets without changing the underlying words.
    if "\n" not in rendered and not rendered.startswith(("• ", "- ", "* ")) and len(rendered) >= 220:
        protected = re.sub(r"\b(Pvt|Ltd|Mr|Mrs|Ms|Dr|Prof|No|Cr)\.", lambda m: m.group(1) + "§", rendered)
        sentences = [x.strip().replace("§", ".") for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9₹])", protected) if x.strip()]
        if len(sentences) >= 3:
            return "\n".join(f"• {x}" for x in sentences)
    return rendered
