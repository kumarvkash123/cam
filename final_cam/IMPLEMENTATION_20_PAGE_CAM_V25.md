# 20-Page CAM / Get -> Verify -> Calculate implementation

Implemented in the existing Flask + Next.js CAM codebase.

## Flow

1. Borrower uploads source documents, especially the Annual Report.
2. Annual Report is classified separately and raw financial/company fields are extracted.
3. A normalized CAM dataset is built from all uploaded evidence.
4. FileSure/MCA is called first for company verification.
5. For the Lactose POC only, if FileSure is unavailable, a clearly labelled synthetic verification provider is used.
6. Field reconciliation records document value vs verified value with MATCH / PARTIAL_MATCH / MISMATCH / NOT_VERIFIED status.
7. Python calculates financial ratios from source-extracted raw values.
8. Existing CAM analysis modules continue to create narrative/analysis.
9. Final CAM generation produces a fixed 20-page appraisal-note structure and includes a source/verification audit trail.

## Important source rule

Synthetic verification never pretends to be real MCA data. The payload contains `_meta.synthetic=true`, and the Borrower Information UI shows a warning when synthetic fallback is used.

## New modules

- `backend/app/cam/extraction_ext/annual_report_extractor.py`
- `backend/app/cam/normalized/builder.py`
- `backend/app/cam/verification/service.py`
- `backend/app/cam/verification/synthetic_provider.py`
- `backend/app/cam/final_cam/generator.py`

## Updated modules

- `backend/app/rules_config.json`
- `backend/app/cam/field_extraction.py`
- `backend/app/cam/mca_service.py`
- `backend/app/cam/core.py`
- `backend/app/cam/borrower_info/service.py`
- `frontend/modules/cam/borrower-information/components.js`
- `frontend/modules/cam/steps/Step6.js`

## POC Lactose fallback verification

The synthetic provider includes company-master-shaped test data plus private verification placeholders for account conduct, credit bureau, GST status and collateral. These are used only if real FileSure data is unavailable and are labelled `synthetic_poc`.

## Validation performed

- Python source compilation completed successfully.
- 20-page CAM generator smoke test generated exactly 20 pages and was rendered successfully with LibreOffice/docx QA tooling.
- Frontend production build reached Next.js compilation but could not complete in this offline environment because Next attempted to download the platform SWC binary from npm.
