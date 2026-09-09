"""
Rule-based document classifier.

Loads rules_config.json, scores extracted text + layout signals against every
doc_type, and returns a ranked list of candidates with confidence scores.

Design principles (see architecture discussion):
- No single signal decides the outcome; scores are additive across regex,
  keyword, layout, and negative-keyword signals.
- Fuzzy keyword matching absorbs common OCR misreads ("UDAI" for "UIDAI").
- Negative signals actively separate confusable pairs (PAN vs Aadhaar,
  GSTR-1 vs GSTR-3B, Balance Sheet vs P&L).
- Thresholds map to three outcomes: auto_accept / needs_review / llm_fallback.
"""

import json
import os
from pathlib import Path
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any

from rapidfuzz import fuzz

CONFIG_PATH = Path(__file__).resolve().parent.parent / "rules_config.json"


@dataclass
class ClassificationResult:
    doc_type: str
    display_name: str
    score: float
    matched_signals: List[str] = field(default_factory=list)
    all_candidates: List[Dict[str, Any]] = field(default_factory=list)
    decision: str = "needs_review"  # auto_accepted | needs_review | llm_fallback


def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _fuzzy_contains(text: str, term: str, threshold: int = 82) -> bool:
    """
    Checks whether `term` appears in `text` allowing for OCR noise.
    Cheap approach: sliding window isn't necessary for short docs; we use
    partial_ratio which is robust to substrings and minor character errors.
    """
    if term.lower() in text.lower():
        return True
    return fuzz.partial_ratio(term.lower(), text.lower()) >= threshold


def _score_doc_type(text: str, layout: dict, doc_cfg: dict, filename: str = "") -> (float, List[str]):
    score = 0.0
    matched = []

    # Filename is strong evidence for business documents because many corporate
    # filings use stable names (MGT-7, Shareholding Pattern, Annual Report, etc.).
    # It is additive rather than a hard override, so text can still correct a bad filename.
    for fsignal in doc_cfg.get("filename_signals", []):
        pattern = fsignal.get("pattern")
        terms = fsignal.get("terms", [])
        weight = float(fsignal.get("weight", 0))
        fname = (filename or "").lower()
        hit = False
        if pattern and re.search(pattern, filename or "", flags=re.I):
            hit = True
            matched.append(f"filename_regex:{pattern}")
        elif terms and any(str(t).lower() in fname for t in terms):
            hit = True
            matched.append(f"filename:{next(t for t in terms if str(t).lower() in fname)}")
        if hit:
            score += weight

    for signal in doc_cfg["signals"]:
        sig_type = signal["type"]
        weight = signal["weight"]

        if sig_type == "regex":
            if re.search(signal["pattern"], text):
                score += weight
                matched.append(f"regex:{signal['pattern']}")

        elif sig_type == "keyword":
            terms = signal["terms"]
            fuzzy = signal.get("fuzzy", False)
            hit = False
            for term in terms:
                if fuzzy and _fuzzy_contains(text, term):
                    hit = True
                    matched.append(f"keyword(fuzzy):{term}")
                    break
                elif not fuzzy and term.lower() in text.lower():
                    hit = True
                    matched.append(f"keyword:{term}")
                    break
            if hit:
                score += weight

        elif sig_type == "negative_keyword":
            terms = signal["terms"]
            for term in terms:
                if term.lower() in text.lower() or _fuzzy_contains(text, term, threshold=88):
                    score += weight  # weight is already negative in config
                    matched.append(f"negative:{term}")
                    break

        elif sig_type == "layout":
            cue = signal["cue"]
            if layout.get(cue):
                score += weight
                matched.append(f"layout:{cue}")

    return score, matched


def classify(text: str, layout: dict, filename: str = "") -> ClassificationResult:
    config = _load_config()
    thresholds = config["thresholds"]

    candidates = []
    for doc_cfg in config["doc_types"]:
        score, matched = _score_doc_type(text, layout, doc_cfg, filename=filename)
        candidates.append({
            "doc_type": doc_cfg["doc_type"],
            "display_name": doc_cfg["display_name"],
            "score": round(score, 2),
            "matched_signals": matched,
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    top = candidates[0] if candidates else {
        "doc_type": "unknown", "display_name": "Unknown", "score": 0, "matched_signals": []
    }

    if top["score"] >= thresholds["auto_accept"]:
        decision = "auto_accepted"
    elif top["score"] >= thresholds["needs_review"]:
        decision = "needs_review"
    else:
        decision = "llm_fallback"

    return ClassificationResult(
        doc_type=top["doc_type"],
        display_name=top["display_name"],
        score=top["score"],
        matched_signals=top["matched_signals"],
        all_candidates=candidates[:5],  # top 5 for review UI / LLM fallback shortlist
        decision=decision,
    )
