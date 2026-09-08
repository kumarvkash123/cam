"""Google web search integration for the CAM Assistant.

The Google credentials stay on the Flask backend. The frontend never receives
GOOGLE_API_KEY or GROQ_API_KEY.
"""
import os
from typing import Any, Dict, List

import requests

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


def google_search(query: str, num_results: int = 6) -> List[Dict[str, Any]]:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    cse_id = os.getenv("GOOGLE_CSE_ID", "").strip()
    if not api_key or not cse_id:
        raise RuntimeError(
            "Google web search is not configured. Set GOOGLE_API_KEY and GOOGLE_CSE_ID in backend/.env."
        )

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": max(1, min(int(num_results), 10)),
        "safe": "active",
    }
    response = requests.get(GOOGLE_SEARCH_URL, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()

    results: List[Dict[str, Any]] = []
    for item in payload.get("items", []):
        results.append(
            {
                "title": item.get("title", "Untitled result"),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "display_link": item.get("displayLink", ""),
            }
        )
    return results
