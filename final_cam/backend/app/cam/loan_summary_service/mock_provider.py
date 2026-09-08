import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional


def _data_root() -> Path:
    configured = os.getenv("CAM_MOCK_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / "demo_data" / "loan_summary"


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _index() -> Dict[str, Any]:
    return _load_json(_data_root() / "mock_api_index.json")


def resolve_company(company_name: str = "", cin: str = "") -> Optional[Dict[str, Any]]:
    name_key, cin_key = _norm(company_name), _norm(cin)
    companies = _index().get("companies") or []
    for item in companies:
        if cin_key and _norm(item.get("cin")) == cin_key:
            return item
    for item in companies:
        if name_key and _norm(item.get("name")) == name_key:
            return item
    for item in companies:
        candidate = _norm(item.get("name"))
        if name_key and candidate and (name_key in candidate or candidate in name_key):
            return item
    return None


def get_mock_bundle(company_name: str = "", cin: str = "") -> Dict[str, Any]:
    company = resolve_company(company_name, cin)
    if not company:
        return {"matched": False, "company": None, "api": {}, "derived": {}, "public": {}}
    base = _data_root() / "companies" / company["slug"]
    api = {p.stem: _load_json(p) for p in sorted((base / "api").glob("*.json"))}
    derived = {p.stem: _load_json(p) for p in sorted((base / "derived").glob("*.json"))}
    return {
        "matched": True,
        "company": company,
        "api": api,
        "derived": derived,
        "public": {
            "company_news": api.get("public_company_news_response", {}),
            "credit_rating": api.get("credit_rating_response", {}),
            "industry_news": api.get("industry_news_response", {}),
            "adverse_media": api.get("adverse_media_response", {}),
        },
    }
