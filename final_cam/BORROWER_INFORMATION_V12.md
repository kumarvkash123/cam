# Borrower Information V12

## What was implemented
- New modular Step 6 Borrower Information service and BOB-style UI.
- Dedicated API: `GET /api/cam/borrower-information/<session_id>` with `?refresh=1` support.
- Source provenance per field and per source.
- Distinct statuses: Official Source, Fetched, Verified, Validated, Processed, Review Required, Pending.
- Deterministic cross-source comparison for CIN, company name, PAN and GSTIN.
- MCA/FileSure data is no longer automatically called "Verified" merely because it was fetched.
- Mock/hybrid/live external-data providers are reused from the existing Loan Summary integration.
- Public information is reused from the existing public-search service.
- Groq creates only the Borrower Overview narrative and CAM Copilot answers; it does not invent identifiers or verification outcomes.
- Step 6 is precomputed in the background after Loan Summary becomes available, so it is normally ready while the user reviews Step 5.
- Single right-side Copilot drawer; no duplicate CAM Assistant.
- Existing report-builder compatibility is retained through the `borrower_details` legacy response shape.

## Source priority
1. Bank internal / CAM state
2. Reviewed uploaded documents
3. Official/external API data (MCA/FileSure, GST, PAN, Udyam)
4. Annual report / company disclosures when available in extracted evidence
5. Public information search
6. Synthetic POC data only when CAM_DATA_MODE permits it

## AI boundary
Groq is used for a concise borrower narrative and question answering. CIN, PAN, GSTIN, company status, incorporation date, business vintage, source status and cross-source verification remain deterministic/source-based.
