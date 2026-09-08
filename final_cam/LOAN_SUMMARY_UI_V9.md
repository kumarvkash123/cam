# Loan Summary UI V9 — Bank of Baroda Dashboard

Implemented on top of the working Groq v8 baseline.

## What changed
- Rebuilt Step 5 in BOB orange / navy / white style.
- Borrower banner with CIN/GSTIN/PAN, customer status and borrower-profile action.
- Three-column top dashboard: Loan Details, Key Financial Indicators and deterministic CAM Readiness donut.
- Added Revenue & PAT trend chart using existing extracted multi-year financial data (no LLM calculation and no chart dependency).
- Added Recent Activities card from the existing Loan Summary payload.
- Preserved the working Groq-only Executive Credit Summary and v8 error visibility; deterministic narrative fallback was NOT reintroduced.
- Preserved Credit & Banking, Risks & Mitigants, Collateral, Compliance and Public Information.
- Removed the old always-visible full-width CAM Assistant from Step 5.
- Added a single right-side CAM Assistant drawer. It opens from Ask Copilot / Open CAM Assistant and reuses the existing `/api/cam/chat/<session_id>` endpoint and chat state.
- Suggested questions can send text directly through the existing `sendCamChat` function.
- Added print-friendly Export Summary action using browser print/PDF workflow.
- Added View CAM Readiness -> Step 4, View Borrower Profile -> Step 6, Back -> Step 4 and Proceed -> Step 6.
- Backend Loan Summary readiness now also returns `missing_items` for the UI.

## Existing integration preserved
Documents -> OCR/extraction -> normalized data -> deterministic financial/risk outputs -> external/mock APIs -> public search -> Loan Summary context -> Groq executive narrative.
