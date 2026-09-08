"""Compatibility wrapper for the modular Borrower Information service."""
from typing import Any, Dict, List
from app.cam.borrower_info import build_borrower_profile


def build_borrower_information(state: Dict[str, Any], documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    return build_borrower_profile(state, documents, include_ai=False)
