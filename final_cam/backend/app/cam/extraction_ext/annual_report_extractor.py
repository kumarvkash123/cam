from __future__ import annotations
import re
from typing import Any, Dict, Optional, Sequence, Tuple, List


def _clean_number(value: str) -> Optional[float]:
    if value is None:
        return None
    s = str(value).replace(',', '').replace('₹', '').strip()
    s = re.sub(r'(?i)\b(rs\.?|inr|lakhs?|lacs?|crores?|cr)\b', '', s).strip()
    neg = s.startswith('(') and s.endswith(')')
    s = s.strip('() ')
    m = re.search(r'-?\d+(?:\.\d+)?', s)
    if not m:
        return None
    v = float(m.group())
    return -abs(v) if neg else v


def _first_pattern(text: str, patterns: Sequence[str]):
    for p in patterns:
        m = re.search(p, text, re.I | re.M)
        if m:
            return m.group(1).strip()
    return None


def _numeric_tokens(value: str):
    """Return numeric tokens from one table-row fragment.

    Financial statements commonly include a Note No. before the current and
    previous year values, e.g. ``Revenue from Operations 28 16,329.01 11,639.93``.
    The old extractor treated ``28`` as revenue.  We preserve all tokens here
    and let the row parser deliberately choose the two financial values.
    """
    values = []
    for token in re.findall(r'\(?-?\d[\d,]*(?:\.\d+)?\)?', value or ''):
        n = _clean_number(token)
        if n is not None:
            values.append(n)
    return values


def _looks_like_note_number(value: float) -> bool:
    """Return True for the small integer tokens commonly used as Note Nos."""
    return float(value).is_integer() and 0 <= abs(value) <= 999


def _row_two_year_values(text: str, label_patterns: Sequence[str]) -> Tuple[Optional[float], Optional[float]]:
    """Extract current/previous year values from a financial-statement row.

    Annual-report PDF text often renders one logical row across multiple lines::

        Revenue from Operations
        28
        16,329.01
        11,639.93

    The first number is the Note No., not the amount.  The previous implementation
    returned as soon as it saw two numbers, so it could incorrectly return
    ``28`` and ``16,329.01``.  This parser gathers the whole logical row first and
    then selects the final two amount columns.
    """
    lines = [ln.strip() for ln in (text or '').splitlines()]
    for label in label_patterns:
        pattern = re.compile(label, re.I)
        for idx, line in enumerate(lines):
            m = pattern.search(line)
            if not m:
                continue

            fragments = [line[m.end():]]
            # Collect continuation lines until the next clear alphabetic row.
            # Four lines covers label -> note -> current -> previous in common
            # PyMuPDF/PDF text extraction while staying local to the row.
            for j in range(idx + 1, min(idx + 5, len(lines))):
                nxt = lines[j]
                current_nums = _numeric_tokens(' '.join(fragments))
                if current_nums and re.match(r'^[A-Za-z][A-Za-z /&().,\-]{3,}', nxt) and not re.match(r'^(?:Rs\.?|INR|₹)', nxt, re.I):
                    break
                fragments.append(nxt)

            nums = _numeric_tokens(' '.join(fragments))
            if len(nums) >= 3 and _looks_like_note_number(nums[0]):
                # note no. + current year + previous year
                return nums[-2], nums[-1]
            if len(nums) >= 2:
                # rows without a note number
                return nums[-2], nums[-1]
    return None, None

def _section(text: str, starts: Sequence[str], ends: Sequence[str], expected_labels: Sequence[str] = ()) -> str:
    """Isolate the most likely audited financial-statement section.

    Annual reports repeat headings in the table of contents and notes.  The old
    implementation always selected the last heading, which can land inside the
    notes.  We now score every candidate heading using the presence of expected
    financial-row labels in the following text and select the strongest match.
    """
    t = text or ''
    candidates: List[int] = []
    for pat in starts:
        candidates.extend(m.start() for m in re.finditer(pat, t, re.I))
    candidates = sorted(set(candidates))
    if not candidates:
        return t

    best_pos = candidates[0]
    best_score = -1
    for pos in candidates:
        # 20k characters is enough to cover a statement while avoiding most
        # remote note sections in normal annual-report text extraction.
        window = t[pos:pos + 20000]
        score = 0
        for label in expected_labels:
            if re.search(label, window, re.I):
                score += 1
        # Prefer a candidate that is followed by a plausible next statement.
        for end_pat in ends:
            m = re.search(end_pat, window[100:], re.I)
            if m:
                score += 1
                break
        if score > best_score:
            best_score = score
            best_pos = pos

    end_pos = None
    tail = t[best_pos + 1:]
    for pat in ends:
        m = re.search(pat, tail, re.I)
        if m:
            candidate = best_pos + 1 + m.start()
            if candidate > best_pos + 100:
                end_pos = candidate if end_pos is None else min(end_pos, candidate)
    return t[best_pos:end_pos] if end_pos else t[best_pos:best_pos + 25000]


def extract_annual_report_fields(text: str) -> Dict[str, Any]:
    """Extract raw source facts from an annual report.

    Financial line items remain in the published statement unit.  No CAM ratio
    is calculated here.  Derived values and unit conversion happen only in the
    deterministic Loan Summary/financial calculation layer.
    """
    t = text or ''
    out: Dict[str, Any] = {'document_kind': 'annual_report'}

    cin = re.search(r'\b[LUF]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b', t, re.I)
    if cin:
        out['cin'] = cin.group().upper()

    name = _first_pattern(t, [
        r'(?im)^\s*([A-Z][A-Za-z ()&.,-]+Limited)\s*$',
        r'(?im)Name of (?:the )?Company\s*[:\-]\s*([^\n]+)',
    ])
    if name:
        out['company_name'] = name

    m = re.search(r'(?i)annual report\s*(20\d{2})\s*[-–]\s*(\d{2,4})', t)
    if m:
        out['financial_year'] = f"{m.group(1)}-{m.group(2)[-2:]}"

    # Detect the financial-statement unit, preferring explicit statement-level
    # wording.  This is metadata only; values below remain unconverted.
    unit = 'raw'
    if re.search(r'(?i)(?:₹|rs\.?)?\s*(?:amounts?\s+)?(?:in\s+)?lakhs?|rs\.?\s+in\s+lakhs?', t):
        unit = 'INR_LAKH'
    elif re.search(r'(?i)(?:₹|rs\.?)?\s*(?:amounts?\s+)?(?:in\s+)?crores?|rs\.?\s+in\s+crores?', t):
        unit = 'INR_CRORE'
    elif re.search(r'(?i)amounts?\s+in\s+rupees|figures?\s+in\s+rupees', t):
        unit = 'INR_RUPEE'
    out['financial_unit'] = unit

    address = _first_pattern(t, [
        r'(?is)Registered Office(?:\s*&\s*Works)?\s*[:\-]?\s*(.{0,350}?)(?:\n\s*(?:CIN|ISIN|BSE|Tel|Phone|Website|Email|Corporate|Financial\s+Year))'
    ])
    if address:
        out['registered_office'] = ' '.join(address.split())

    balance = _section(
        t,
        [r'BALANCE\s+SHEET\s+AS\s+AT', r'\bBALANCE\s+SHEET\b'],
        [r'STATEMENT\s+OF\s+PROFIT\s+AND\s+LOSS', r'PROFIT\s+AND\s+LOSS'],
        [r'TOTAL\s+ASSETS', r'Total\s+current\s+assets', r'Total\s+equity', r'Current\s+borrowings'],
    )
    profit_loss = _section(
        t,
        [r'STATEMENT\s+OF\s+PROFIT\s+AND\s+LOSS', r'PROFIT\s+AND\s+LOSS'],
        [r'CASH\s+FLOW\s+STATEMENT', r'STATEMENT\s+OF\s+CASH\s+FLOWS?'],
        [r'Revenue\s+from\s+Operations', r'Total\s+Income', r'Profit\s+before\s+tax', r'Finance\s+Costs?'],
    )
    cash_flow = _section(
        t,
        [r'CASH\s+FLOW\s+STATEMENT', r'STATEMENT\s+OF\s+CASH\s+FLOWS?'],
        [r'NOTES?\s+TO\s+(?:THE\s+)?FINANCIAL\s+STATEMENTS', r'STATEMENT\s+OF\s+CHANGES\s+IN\s+EQUITY'],
        [r'Net\s+Cash.*?Operating\s+Activities', r'Net\s+Cash.*?Investing\s+Activities', r'Net\s+Cash.*?Financing\s+Activities'],
    )

    mappings = {
        'profit_loss': {
            'revenue_from_operations': [r'Revenue\s+from\s+Operations'],
            'other_income': [r'Other\s+Income'],
            'total_income': [r'Total\s+Income'],
            'total_expenses': [r'Total\s+Expenses?'],
            'profit_before_tax': [r'Profit\s+before\s+tax'],
            'profit_after_tax': [r'Profit\s+(?:for\s+the\s+year|after\s+tax)', r'Net\s+Profit.*?after\s+Tax'],
            'finance_cost': [r'Finance\s+Costs?'],
            'depreciation_amortisation': [r'Depreciation\s+and\s+amortisation(?:\s+expenses?)?'],
        },
        'balance': {
            'equity_share_capital': [r'Equity\s+Share\s+capital'],
            'other_equity': [r'Other\s+equity'],
            'total_equity': [r'Total\s+equity'],
            'total_assets': [r'TOTAL\s+ASSETS'],
            'total_current_assets': [r'Total\s+current\s+assets'],
            'total_current_liabilities': [r'Total\s+current\s+liabilities'],
            'inventories': [r'Inventories'],
            'trade_receivables': [r'Trade\s+receivables'],
            'trade_payables': [r'Trade\s+payables'],
            'cash_and_cash_equivalents': [r'Cash\s+and\s+cash\s+equivalents'],
            'non_current_borrowings': [r'Non[-\s]?current\s+borrowings'],
            'current_borrowings': [r'(?<!Non[-–])(?<!Non\s)Current\s+borrowings'],
        },
        'cash_flow': {
            'net_cash_from_operating_activities': [r'Net\s+Cash\s+Flow\s+from\s+Operating\s+Activities', r'Net\s+cash.*?operating\s+activities'],
            'net_cash_from_investing_activities': [r'Net\s+Cash\s+Flow\s+from\s+Investing\s+Activities', r'Net\s+cash.*?investing\s+activities'],
            'net_cash_from_financing_activities': [r'Net\s+Cash\s+Flow\s+from\s+Financing\s+Activities', r'Net\s+cash.*?financing\s+activities'],
        },
    }
    section_text = {'balance': balance, 'profit_loss': profit_loss, 'cash_flow': cash_flow}
    for section_name, mapping in mappings.items():
        source = section_text[section_name]
        for key, patterns in mapping.items():
            a, b = _row_two_year_values(source, patterns)
            if a is not None:
                out[f'{key}_current'] = a
            if b is not None:
                out[f'{key}_previous'] = b

    auditor = _first_pattern(t, [
        r'(?i)Statutory Auditors?\s*[:\-]\s*([^\n]+)',
        r'(?i)Auditors?\s*[:\-]\s*([^\n]+)',
    ])
    if auditor:
        out['statutory_auditor'] = auditor
    md = _first_pattern(t, [r'(?i)(Atul\s+Maheshwari)\s*[-–,]\s*Managing\s+Director'])
    if md:
        out['managing_director'] = md
    cfo = _first_pattern(t, [r'(?i)(Sangita\s+Maheshwari).*?(?:CFO|Chief\s+Financial\s+Officer)'])
    if cfo:
        out['cfo_or_wtd'] = cfo

    return {k: v for k, v in out.items() if v not in (None, '')}
