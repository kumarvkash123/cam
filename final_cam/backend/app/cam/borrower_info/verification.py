import re
from typing import Any, Dict, Optional


def clean_identifier(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def clean_name(value: Any) -> str:
    text = str(value or "").lower()
    replacements = {"private limited": "pvt ltd", "pvt. ltd.": "pvt ltd", "pvt. ltd": "pvt ltd", "limited": "ltd"}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r"[^a-z0-9]", "", text)


def verify_exact(primary: Any, comparison: Any, *, official: bool = False) -> Dict[str, Any]:
    if primary in (None, ""):
        return {"status": "pending", "matched": False}
    if comparison in (None, ""):
        return {"status": "official_source" if official else "fetched", "matched": False}
    matched = clean_identifier(primary) == clean_identifier(comparison)
    return {"status": "verified" if matched else "review_required", "matched": matched}


def verify_name(primary: Any, comparison: Any, *, official: bool = False) -> Dict[str, Any]:
    if primary in (None, ""):
        return {"status": "pending", "matched": False}
    if comparison in (None, ""):
        return {"status": "official_source" if official else "fetched", "matched": False}
    matched = clean_name(primary) == clean_name(comparison)
    return {"status": "verified" if matched else "review_required", "matched": matched}


def field(value: Any, source: str, status: str, *, source_type: str = "", note: Optional[str] = None) -> Dict[str, Any]:
    return {
        "value": value,
        "source": source,
        "source_type": source_type or source,
        "status": status,
        "note": note,
    }
