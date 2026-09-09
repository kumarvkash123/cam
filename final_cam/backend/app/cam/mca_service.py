"""MCA company-data adapter for the CAM POC.

The API key is read from the MCA_API_KEY environment variable and is never
returned to the browser.  FileSure is used as the POC provider because its
current API exposes MCA company master data by CIN.
"""

import os
from app.config import get_mca_api_key, get_mca_base_url
import re
from typing import Any, Dict, Optional

import requests

DEFAULT_BASE_URL = "https://api.filesure.in"
CIN_RE = re.compile(r"\b[LUF]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b", re.IGNORECASE)


def normalize_cin(value: str) -> Optional[str]:
    if not value:
        return None
    match = CIN_RE.search(str(value).upper().replace(" ", ""))
    return match.group(0) if match else None


def find_cin_in_value(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return normalize_cin(value)
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in {"cin", "companycin", "corporate_identity_number", "corporateidentitynumber"}:
                found = normalize_cin(str(item))
                if found:
                    return found
            found = find_cin_in_value(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_cin_in_value(item)
            if found:
                return found
    return None


def _headers(api_key: str) -> Dict[str, str]:
    # FileSure's current documentation shows x-api-key authentication.
    return {"x-api-key": api_key, "Accept": "application/json"}


def get_company_by_cin(cin: str) -> Dict[str, Any]:
    api_key = get_mca_api_key()
    if not api_key:
        raise RuntimeError("MCA_API_KEY is not configured. Add your MCA API key to the environment before fetching MCA data.")

    normalized = normalize_cin(cin)
    if not normalized:
        raise ValueError("A valid 21-character CIN is required to fetch MCA company data.")

    base_url = get_mca_base_url() or DEFAULT_BASE_URL
    url = f"{base_url}/v1/companies/{normalized}"

    try:
        response = requests.get(url, headers=_headers(api_key), timeout=20)
    except requests.RequestException as exc:
        raise RuntimeError(f"Unable to connect to MCA data provider: {exc}") from exc

    if response.status_code == 401:
        raise RuntimeError("MCA API authentication failed. Check MCA_API_KEY.")
    if response.status_code == 403:
        raise RuntimeError("MCA API access is forbidden for this key.")
    if response.status_code == 404:
        raise RuntimeError(f"No MCA company record was found for CIN {normalized}.")
    if response.status_code == 429:
        raise RuntimeError("MCA API rate limit reached. Please try again later.")
    if response.status_code >= 400:
        detail = response.text[:500].strip()
        raise RuntimeError(f"MCA API returned HTTP {response.status_code}: {detail}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("MCA API returned a non-JSON response.") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected MCA API response format.")

    return payload


def get_company_by_cin_with_fallback(cin: str, allow_synthetic: bool = True) -> Dict[str, Any]:
    """Use FileSure first; for the Lactose POC only, return clearly-labelled synthetic verification when unavailable."""
    try:
        payload = get_company_by_cin(cin)
        if isinstance(payload, dict):
            payload.setdefault("_meta", {})
            payload["_meta"].update({"provider": "FileSure / MCA", "synthetic": False, "verified": True})
        return payload
    except Exception as exc:
        if not allow_synthetic:
            raise
        from app.cam.verification.synthetic_provider import LACTOSE_CIN, lactose_company_master
        normalized = normalize_cin(cin)
        if normalized == LACTOSE_CIN:
            payload = lactose_company_master()
            payload.setdefault("_meta", {})["filesure_error"] = str(exc)
            return payload
        raise
