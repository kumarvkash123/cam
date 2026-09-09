"""
Pulls out key fields per doc_type and masks sensitive identifiers before
they're stored. Full unmasked values should only ever live transiently in
memory during verification (e.g. a one-time API call to validate against
NSDL/UIDAI), never persisted in plaintext.

NOTE ON AADHAAR: Storing raw Aadhaar numbers is legally restricted unless
you are UIDAI-authorized (AUA/KUA licensed). This POC only ever stores a
masked form (last 4 digits) -- treat that as a hard requirement, not a
suggestion, until you've confirmed your entity's authorization status.
"""

import re
from typing import Dict, Optional
from app.cam.extraction_ext import extract_annual_report_fields


def _mask_middle(value: str, keep_start: int = 0, keep_end: int = 4) -> str:
    if len(value) <= keep_start + keep_end:
        return "*" * len(value)
    return value[:keep_start] + "*" * (len(value) - keep_start - keep_end) + value[-keep_end:]


_AMOUNT_RE = re.compile(r"\d{1,3}(?:,\d{2,3})*\.\d{2}")


def _extract_amount_after_label(text: str, labels: list) -> Optional[str]:
    """
    Finds the LAST occurrence of any given label in the text and returns the
    first currency-formatted amount (e.g. "1,250,000.00") that appears within
    a short window after it. Placeholder characters like "-" are skipped
    automatically since they don't match the amount pattern.

    Using the last occurrence (rather than the first) matters here: labels
    like "Opening Balance" / "Closing Balance" often appear once inside the
    transaction table AND once in a summary section -- the summary section
    (which comes later in the document) is the more reliable source.
    """
    best = None
    for label in labels:
        for m in re.finditer(re.escape(label), text, re.IGNORECASE):
            window = text[m.end(): m.end() + 100]
            amt_match = _AMOUNT_RE.search(window)
            if amt_match:
                best = amt_match.group()
    return best


def _extract_line_after_label(text: str, label: str) -> Optional[str]:
    """Grabs the text on the line immediately following a label, e.g.
    'Account Holder\\nACME TRADING PRIVATE LIMITED' -> 'ACME TRADING PRIVATE LIMITED'."""
    m = re.search(re.escape(label) + r"\s*\n\s*(.+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else None



def _clean_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip(" :-\t\r\n")
    return value or None


def _extract_named_value(text: str, labels: list[str], max_chars: int = 500) -> Optional[str]:
    """Extract a value immediately following a form/table label.

    Works for text extracted from two-column PDFs where a label and value may be
    on the same line or on adjacent lines.  It intentionally stops at the next
    known form label rather than consuming narrative text.
    """
    labels_escaped = "|".join(re.escape(x) for x in labels)
    next_labels = [
        "Cam Id", "Application Date", "Facility", "Requested Amount Cr",
        "Requested Amount", "Loan Amount", "Purpose", "Tenor Months",
        "Tenure Months", "Moratorium Months", "Repayment", "Pricing",
        "Interest Rate", "Processing Fee Pct", "Processing Fee",
        "Primary Security", "Collateral", "Declaration"
    ]
    stop = "|".join(re.escape(x) for x in next_labels)
    pattern = re.compile(
        rf"(?:^|\n)\s*(?:{labels_escaped})\s*[:\-]?\s*(?:\n\s*)?(.*?)"
        rf"(?=(?:\n\s*(?:{stop})\s*[:\-]?)|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(text or "")
    if not m:
        return None
    return _clean_value(m.group(1)[:max_chars])


def _extract_decimal(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    m = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", str(value))
    if not m:
        return None
    try:
        return float(m.group().replace(",", ""))
    except ValueError:
        return None


def _extract_loan_application_fields(text: str) -> Dict[str, object]:
    """Extract only borrower-provided proposal terms from a loan application.

    Values stay in the units printed on the form.  In particular, fields named
    `*_cr` are already in crore and must NOT be treated as rupee amounts later.
    """
    out: Dict[str, object] = {"document_kind": "loan_application"}

    facility = _extract_named_value(text, ["Facility", "Facility Type", "Loan Type"])
    amount_raw = _extract_named_value(text, ["Requested Amount Cr", "Requested Amount", "Loan Amount"])
    purpose = _extract_named_value(text, ["Purpose", "Purpose of Loan"])
    tenure_raw = _extract_named_value(text, ["Tenor Months", "Tenure Months", "Tenure"])
    moratorium_raw = _extract_named_value(text, ["Moratorium Months", "Moratorium"])
    repayment = _extract_named_value(text, ["Repayment", "Repayment Structure"])
    pricing = _extract_named_value(text, ["Pricing", "Interest Rate", "Rate of Interest"])
    fee_raw = _extract_named_value(text, ["Processing Fee Pct", "Processing Fee"])
    primary_security = _extract_named_value(text, ["Primary Security", "Security"])
    collateral = _extract_named_value(text, ["Collateral"])
    application_date = _extract_named_value(text, ["Application Date"])
    cam_id = _extract_named_value(text, ["Cam Id", "CAM ID"])

    amount = _extract_decimal(amount_raw)
    tenure = _extract_decimal(tenure_raw)
    moratorium = _extract_decimal(moratorium_raw)
    fee = _extract_decimal(fee_raw)

    if facility:
        out["facility_type"] = facility
        out["proposal_type"] = "Fresh" if re.search(r"\bfresh\b", facility, re.I) else None
    if amount is not None:
        # The preferred test form explicitly labels this field in crore.
        if re.search(r"Requested Amount Cr", text or "", re.I):
            out["requested_amount_cr"] = amount
        else:
            # Preserve the raw amount for downstream normalization where the
            # source label did not declare a unit.
            out["requested_amount_raw"] = amount
            out["requested_amount_text"] = amount_raw
    if purpose:
        out["purpose"] = purpose
    if tenure is not None:
        out["tenure_months"] = int(tenure) if tenure.is_integer() else tenure
    if moratorium is not None:
        out["moratorium_months"] = int(moratorium) if moratorium.is_integer() else moratorium
    if repayment:
        out["repayment"] = repayment
    if pricing:
        out["pricing"] = pricing
        rate = re.search(r"(\d+(?:\.\d+)?)\s*%", pricing)
        if rate:
            out["interest_rate_pct"] = float(rate.group(1))
    if fee is not None:
        out["processing_fee_pct"] = fee
    if primary_security:
        out["primary_security"] = primary_security
    if collateral:
        out["collateral"] = collateral
    if application_date:
        out["application_date"] = application_date
    if cam_id:
        out["source_cam_id"] = cam_id

    return {k: v for k, v in out.items() if v not in (None, "")}

def extract_fields(doc_type: str, text: str) -> Dict[str, Optional[str]]:
    fields = {}

    # CIN is a public company identifier and is used to enrich the CAM with
    # MCA company master data. Look for it across all document types because
    # incorporation/MOA documents are not always classified consistently.
    cin = re.search(r"\b[LUF]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b", text or "", re.IGNORECASE)
    if cin:
        fields["cin"] = cin.group().upper()

    if doc_type == "annual_report":
        fields.update(extract_annual_report_fields(text))

    elif doc_type == "loan_application":
        fields.update(_extract_loan_application_fields(text))

    elif doc_type == "pan_card":
        m = re.search(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", text)
        if m:
            fields["pan_number_masked"] = _mask_middle(m.group(), keep_start=0, keep_end=4)

    elif doc_type == "aadhaar_card":
        m = re.search(r"\d{4}\s?\d{4}\s?\d{4}", text)
        if m:
            digits = re.sub(r"\s", "", m.group())
            fields["aadhaar_number_masked"] = "XXXX XXXX " + digits[-4:]
            # fields["aadhaar_number_masked"] = digits

    elif doc_type == "bank_statement":
        ifsc = re.search(r"[A-Z]{4}0[A-Z0-9]{6}", text)
        if ifsc:
            fields["ifsc"] = ifsc.group()  # not sensitive, fine to store in full

        acct = re.search(
            r"(?:A/?C\.?\s*No\.?|Account\s*No\.?|Account\s*Number)\s*[:\-]?\s*\n?\s*([A-Za-z0-9]{6,20})",
            text, re.IGNORECASE,
        )
        if acct:
            fields["account_number_masked"] = _mask_middle(acct.group(1), keep_start=0, keep_end=4)

        opening_balance = _extract_amount_after_label(text, ["Opening Balance"])
        if opening_balance:
            fields["opening_balance"] = opening_balance

        closing_balance = _extract_amount_after_label(text, ["Closing Balance"])
        if closing_balance:
            fields["closing_balance"] = closing_balance

        account_holder = _extract_line_after_label(text, "Account Holder")
        if account_holder:
            fields["account_holder_name"] = account_holder

        statement_period = _extract_line_after_label(text, "Statement Period")
        if statement_period:
            fields["statement_period"] = statement_period

    elif doc_type == "gst_registration_cert" or doc_type in ("gstr_1", "gstr_3b"):
        gstin = re.search(r"\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z0-9]{1}[Z]{1}[A-Z0-9]{1}", text)
        if gstin:
            fields["gstin"] = gstin.group()  # GSTIN is a public business identifier, not masked

    elif doc_type == "udyam_certificate":
        urn = re.search(r"UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}", text)
        if urn:
            fields["udyam_registration_number"] = urn.group()

    elif doc_type == "itr":
        ack = re.search(r"\b\d{12,15}\b", text)
        ay = re.search(r"20\d{2}-\d{2}", text)
        if ack:
            fields["acknowledgement_number"] = ack.group()
        if ay:
            fields["assessment_year"] = ay.group()

    return fields
