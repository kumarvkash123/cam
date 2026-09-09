from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from app.cam.verification import build_verification_bundle
from app.cam.extraction_ext import extract_annual_report_fields


def _merge_fields(documents):
    out = {}
    provenance = {}
    for d in documents:
        for k, v in (d.get('extracted_fields') or {}).items():
            if v not in (None, ''):
                out[k] = v
                provenance[k] = {'document': d.get('original_filename'), 'doc_type': d.get('doc_type')}
    return out, provenance


def _f(v):
    try:
        return float(str(v).replace(',', '').replace('₹', ''))
    except (TypeError, ValueError):
        return None


def _ratio(a, b):
    a, b = _f(a), _f(b)
    return round(a / b, 4) if a is not None and b not in (None, 0) else None


def _fy_key(value: Any):
    m = re.search(r'(20\d{2})\s*[-–/]\s*(\d{2,4})', str(value or ''))
    if not m:
        return (0, 0)
    start, end = int(m.group(1)), int(m.group(2))
    if end < 100:
        end = (start // 100) * 100 + end
    return (end, start)


def _financial_unit_multiplier(unit: Any) -> Optional[float]:
    unit = str(unit or '').upper().strip()
    if unit == 'INR_LAKH':
        return 100_000.0
    if unit == 'INR_CRORE':
        return 10_000_000.0
    if unit == 'INR_RUPEE':
        return 1.0
    return None


def _latest_annual_report_fields(documents):
    candidates = []
    for d in documents:
        stored = d.get('extracted_fields') or {}
        if d.get('doc_type') != 'annual_report' and stored.get('document_kind') != 'annual_report':
            continue
        f = stored
        if d.get('extracted_text'):
            reparsed = extract_annual_report_fields(d.get('extracted_text') or '')
            if any(k.endswith('_current') for k in reparsed):
                f = reparsed
        if any(k.endswith('_current') for k in f):
            candidates.append((d, f))
    if not candidates:
        return None, None
    candidates.sort(key=lambda item: _fy_key(item[1].get('financial_year')), reverse=True)
    return candidates[0]


def _money_raw(fields: Dict[str, Any], key: str):
    return _f(fields.get(key))


def build_normalized_cam_data(state: Dict[str, Any], documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    fields, provenance = _merge_fields(documents)
    verification = build_verification_bundle(state, documents, allow_synthetic=True)

    annual_doc, annual_fields = _latest_annual_report_fields(documents)
    financial_fields = annual_fields or fields
    unit_multiplier = _financial_unit_multiplier(financial_fields.get('financial_unit'))

    ca = _money_raw(financial_fields, 'total_current_assets_current') or _money_raw(financial_fields, 'current_assets_current') or _money_raw(financial_fields, 'current_assets')
    cl = _money_raw(financial_fields, 'total_current_liabilities_current') or _money_raw(financial_fields, 'current_liabilities_current') or _money_raw(financial_fields, 'current_liabilities')
    inventory = _money_raw(financial_fields, 'inventories_current') or _money_raw(financial_fields, 'inventory_current') or _money_raw(financial_fields, 'inventory')
    equity = _money_raw(financial_fields, 'total_equity_current') or _money_raw(financial_fields, 'tangible_net_worth_current') or _money_raw(financial_fields, 'net_worth_current')
    debt_parts = [_money_raw(financial_fields, 'current_borrowings_current'), _money_raw(financial_fields, 'non_current_borrowings_current')]
    debt = sum(x for x in debt_parts if x is not None) if any(x is not None for x in debt_parts) else _money_raw(financial_fields, 'total_debt_current')
    revenue = _money_raw(financial_fields, 'total_income_current') or _money_raw(financial_fields, 'revenue_from_operations_current')
    pat = _money_raw(financial_fields, 'profit_after_tax_current')
    finance = _money_raw(financial_fields, 'finance_cost_current')
    pbt = _money_raw(financial_fields, 'profit_before_tax_current')
    depreciation = _money_raw(financial_fields, 'depreciation_amortisation_current')
    ebitda = (pbt + finance + depreciation) if None not in (pbt, finance, depreciation) else None

    ratios = {
        'current_ratio': _ratio(ca, cl),
        'quick_ratio': round((ca - inventory) / cl, 4) if None not in (ca, inventory) and cl not in (None, 0) else None,
        'debt_equity': _ratio(debt, equity),
        'pat_margin_pct': round((pat / revenue) * 100, 2) if pat is not None and revenue not in (None, 0) else None,
        'ebitda_margin_pct': round((ebitda / revenue) * 100, 2) if ebitda is not None and revenue not in (None, 0) else None,
        'interest_coverage': round(ebitda / finance, 2) if ebitda is not None and finance not in (None, 0) else None,
    }

    return {
        'proposal': {k: state.get(k) for k in ('company_name', 'loan_type', 'loan_amount', 'loan_amount_numeric', 'loan_purpose', 'tenure', 'interest_rate', 'repayment')},
        'raw_fields': fields,
        'provenance': provenance,
        'verification': verification,
        'calculated': {
            'financial_year': financial_fields.get('financial_year'),
            'financial_unit': financial_fields.get('financial_unit'),
            'financial_source_document': annual_doc.get('original_filename') if annual_doc else None,
            'total_debt_raw_unit': debt,
            'ebitda_raw_unit': ebitda,
            'ratios': ratios,
        },
        'documents': [{'file': d.get('original_filename'), 'doc_type': d.get('doc_type'), 'status': d.get('status')} for d in documents],
    }
