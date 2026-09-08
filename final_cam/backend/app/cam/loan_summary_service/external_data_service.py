import os
from typing import Any, Dict
from .mock_provider import get_mock_bundle


def _state_mca(state: Dict[str, Any]) -> Dict[str, Any]:
    mca = state.get("mca") or {}
    if not isinstance(mca, dict):
        return {}
    return mca.get("data") or mca


def collect_external_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """POC external-data switch: mock, hybrid, or live."""
    mode = os.getenv("CAM_DATA_MODE", "mock").strip().lower() or "mock"
    bundle = get_mock_bundle(state.get("company_name") or "", state.get("cin") or "") if mode in ("mock", "hybrid") else {"matched": False, "api": {}, "derived": {}, "public": {}}
    api = dict(bundle.get("api") or {})
    real_mca = _state_mca(state)
    if real_mca and mode in ("live", "hybrid"):
        api["mca_response"] = real_mca
    return {
        "mode": mode,
        "mock_matched": bool(bundle.get("matched")),
        "mock_company": bundle.get("company"),
        "api": api,
        "derived": bundle.get("derived") or {},
        "mock_public": bundle.get("public") or {},
    }
