# Loan Summary data-flow fix V29

This update fixes the three backend issues exposed by the Loan Summary screenshot:

1. Loan Application is now parsed by a document-specific extractor.
2. Loan Summary consumes the extracted proposal fields directly.
3. Corporate CAM readiness no longer marks Aadhaar/Udyam as universally mandatory.

## Proposal source priority

User-confirmed state > uploaded Loan Application > configured proposal API > synthetic POC fallback.

The Loan Application extractor captures facility type, requested amount in crore, purpose,
tenure, moratorium, repayment, pricing/rate, processing fee, primary security and collateral.

Existing sessions are supported: Loan Summary re-parses the stored Loan Application text at
runtime, so a re-upload is not required solely to populate proposal fields after this change.

## Financial indicators

The structured Annual Report financial extraction/unit-normalization fix from V27 is retained.
Loan Summary continues to prefer audited Annual Report statement rows over generic text regex.

## CAM readiness

For a corporate borrower (CIN present), the checklist uses the `corporate` profile. Company-level
readiness no longer treats Aadhaar as a mandatory company document, and Udyam remains MSME-only.
