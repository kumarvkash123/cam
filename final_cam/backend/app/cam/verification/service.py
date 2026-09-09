from __future__ import annotations
from typing import Any, Dict, List
from app.cam import mca_service
from .synthetic_provider import LACTOSE_CIN, lactose_company_master

def _norm(v):
    return ''.join(ch for ch in str(v or '').upper() if ch.isalnum())

def _doc_value(documents: List[Dict[str,Any]], keys):
    wanted={k.lower() for k in keys}
    for d in documents:
        for k,v in (d.get('extracted_fields') or {}).items():
            if str(k).lower() in wanted and v not in (None,''):
                return v, d.get('original_filename') or 'Uploaded document'
    return None,None

def _compare(field, doc_value, verified_value, source, source_kind):
    if doc_value in (None,'') and verified_value in (None,''):
        status='NOT_VERIFIED'
    elif doc_value in (None,''):
        status='VERIFICATION_ONLY'
    elif verified_value in (None,''):
        status='NOT_VERIFIED'
    elif _norm(doc_value)==_norm(verified_value):
        status='MATCH'
    elif _norm(doc_value) in _norm(verified_value) or _norm(verified_value) in _norm(doc_value):
        status='PARTIAL_MATCH'
    else:
        status='MISMATCH'
    return {'field':field,'document_value':doc_value,'verified_value':verified_value,'verification_source':source,'source_kind':source_kind,'status':status}

def build_verification_bundle(state: Dict[str,Any], documents: List[Dict[str,Any]], *, allow_synthetic: bool=True) -> Dict[str,Any]:
    cin,_=_doc_value(documents,['cin'])
    cin=cin or (state.get('mca') or {}).get('cin')
    company,_=_doc_value(documents,['company_name','legal_name'])
    payload=None; source='FileSure / MCA'; source_kind='real_api'; error=None
    if cin:
        try:
            payload=mca_service.get_company_by_cin(cin)
        except Exception as exc:
            error=str(exc)
    if payload is None and allow_synthetic and (cin==LACTOSE_CIN or 'lactose' in str(state.get('company_name') or '').lower()):
        payload=lactose_company_master(); source='Synthetic POC fallback'; source_kind='synthetic_poc'
    company_data={}
    if isinstance(payload,dict):
        p=payload.get('data') if isinstance(payload.get('data'),dict) else payload
        master=(p.get('masterData') or {}) if isinstance(p,dict) else {}
        company_data=master.get('companyData') or p or {}
    verified_cin=company_data.get('cin') or (payload or {}).get('cin') if isinstance(payload,dict) else None
    verified_name=company_data.get('companyName') or (payload or {}).get('company') if isinstance(payload,dict) else None
    address=''; addresses=company_data.get('MCAMDSCompanyAddress') or []
    if addresses:
        a=addresses[0]; address=', '.join(str(a.get(k)).strip() for k in ('addressLine1','addressLine2','city','state','pinCode') if a.get(k))
    doc_address,_=_doc_value(documents,['registered_office','registered_address'])
    doc_paid,_=_doc_value(documents,['paid_up_capital','equity_share_capital_current'])
    rows=[
      _compare('CIN',cin,verified_cin,source,source_kind),
      _compare('Company Name',company or state.get('company_name'),verified_name,source,source_kind),
      _compare('Registered Office',doc_address,address or None,source,source_kind),
      _compare('Paid-up Capital',doc_paid,company_data.get('paidupCapital'),source,source_kind),
    ]
    return {'provider':source,'source_kind':source_kind,'synthetic':source_kind=='synthetic_poc','error_from_real_provider':error,'cin':cin,'raw':payload,'reconciliation':rows,'additional_poc_verification':(payload or {}).get('poc_additional_verification',{}) if isinstance(payload,dict) else {}}
