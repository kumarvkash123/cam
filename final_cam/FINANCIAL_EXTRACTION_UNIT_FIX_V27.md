# Financial Extraction + Unit Normalization Fix V27

## Problem fixed
Loan Summary financial indicators were being built by searching all uploaded document text for nearby numbers. In Annual Reports this could capture Note Nos. instead of values (for example `Revenue from Operations 28 ...` became revenue `28`, and `Inventories 7 ...` became inventory `7`). A document-wide unit guess could then magnify the wrong value and create impossible PAT/EBITDA margins.

## Changes
- Annual Report extractor now isolates Balance Sheet, Statement of Profit & Loss and Cash Flow sections.
- Financial row parsing deliberately skips leading Note Nos. and takes the two actual current/previous year values.
- Loan Summary now prefers the latest structured Annual Report instead of scanning one combined text blob.
- Every annual-report currency value is normalized using explicit `financial_unit` metadata (`INR_LAKH`, `INR_CRORE`, `INR_RUPEE`) before display/calculation.
- EBITDA is deterministically reconstructed as `PBT + Finance Cost + Depreciation/Amortisation` when all three audited source values exist.
- Total Debt = Current Borrowings + Non-current Borrowings.
- Net Worth = Total Equity.
- Current Ratio = Current Assets / Current Liabilities.
- Quick Ratio = (Current Assets - Inventory) / Current Liabilities.
- EBITDA Margin = EBITDA / Total Income × 100.
- PAT Margin = PAT / Total Income × 100.
- Interest Coverage follows the existing CAM convention: EBITDA / Finance Cost.
- Existing CAM sessions do not need document re-upload: Loan Summary and normalized CAM builder re-parse stored Annual Report text with the corrected extractor at runtime.
- Legacy text extraction remains only as a fallback when no usable structured Annual Report exists.

## Expected Lactose FY2025-26 direction
When the source Annual Report contains the audited values used in testing, the resulting indicators should be around:
- Total Income: ₹164.362 Cr
- EBITDA (derived): ₹19.448 Cr
- PAT: ₹6.063 Cr
- Net Worth / Total Equity: ₹64.789 Cr
- Total Debt: ₹61.656 Cr
- Debt / Equity: ~0.95x
- Current Ratio: ~1.10x
- Quick Ratio: ~0.48x
- EBITDA Margin: ~11.83%
- PAT Margin: ~3.69%
- Interest Coverage (existing CAM convention): ~3.82x

The displayed values must still be sourced from the user's uploaded Annual Report, not from hardcoded Lactose values.
