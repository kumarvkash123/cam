"""
Config-driven checklist: which doc_types are mandatory for which loan_type /
amount bracket. Drives the "3 of 8 documents uploaded" progress UI and lets
you reuse the same classifier across products.
"""

REQUIREMENT_MATRIX = [
    # Individual KYC should not be treated as company-level mandatory evidence.
    {"doc_type": "pan_card", "category": "KYC-Individual", "mandatory_for": ["personal"]},
    {"doc_type": "aadhaar_card", "category": "KYC-Individual", "mandatory_for": ["personal"]},
    {"doc_type": "voter_id", "category": "KYC-Individual", "mandatory_for": []},
    {"doc_type": "passport", "category": "KYC-Individual", "mandatory_for": []},

    {"doc_type": "loan_application", "category": "Proposal", "mandatory_for": ["corporate", "msme", "big_ticket", "secured_big_ticket"]},
    {"doc_type": "annual_report", "category": "Financial", "mandatory_for": ["corporate"]},
    {"doc_type": "annual_return_mgt7", "category": "Corporate", "mandatory_for": []},
    {"doc_type": "shareholding_pattern", "category": "Corporate", "mandatory_for": []},
    {"doc_type": "secretarial_compliance", "category": "Compliance", "mandatory_for": []},
    {"doc_type": "audited_financial_results", "category": "Financial", "mandatory_for": []},

    {"doc_type": "udyam_certificate", "category": "KYC-Business", "mandatory_for": ["msme"]},
    {"doc_type": "gst_registration_cert", "category": "KYC-Business", "mandatory_for": ["msme", "big_ticket"]},
    {"doc_type": "partnership_deed", "category": "KYC-Business", "mandatory_for": []},
    {"doc_type": "moa_aoa", "category": "KYC-Business", "mandatory_for": []},
    {"doc_type": "certificate_of_incorporation", "category": "KYC-Business", "mandatory_for": []},

    {"doc_type": "bank_statement", "category": "Financial", "mandatory_for": ["personal", "msme", "big_ticket", "secured_big_ticket"]},
    {"doc_type": "itr", "category": "Financial", "mandatory_for": ["personal", "msme", "big_ticket"]},
    {"doc_type": "balance_sheet", "category": "Financial", "mandatory_for": ["msme", "big_ticket"]},
    {"doc_type": "profit_loss_statement", "category": "Financial", "mandatory_for": ["msme", "big_ticket"]},
    {"doc_type": "gstr_3b", "category": "Financial", "mandatory_for": ["big_ticket"]},
    {"doc_type": "gstr_1", "category": "Financial", "mandatory_for": ["big_ticket"]},

    {"doc_type": "trade_license", "category": "Business Proof", "mandatory_for": []},
    {"doc_type": "shop_establishment_cert", "category": "Business Proof", "mandatory_for": []},
    {"doc_type": "property_papers", "category": "Collateral", "mandatory_for": ["secured", "secured_big_ticket"]},
    {"doc_type": "cibil_report", "category": "Additional", "mandatory_for": ["big_ticket"]},
]



def get_checklist(loan_type: str) -> list:
    checklist = []
    for row in REQUIREMENT_MATRIX:
        is_mandatory = "all" in row["mandatory_for"] or loan_type in row["mandatory_for"]
        checklist.append({**row, "is_mandatory": is_mandatory})
    return checklist


def compute_progress(loan_type: str, uploaded_doc_types: list) -> dict:
    checklist = get_checklist(loan_type)
    mandatory = [c for c in checklist if c["is_mandatory"]]
    uploaded_mandatory = [c for c in mandatory if c["doc_type"] in uploaded_doc_types]
    missing = [c["doc_type"] for c in mandatory if c["doc_type"] not in uploaded_doc_types]

    return {
        "total_mandatory": len(mandatory),
        "uploaded_mandatory": len(uploaded_mandatory),
        "missing_mandatory": missing,
        "checklist": checklist,
    }
