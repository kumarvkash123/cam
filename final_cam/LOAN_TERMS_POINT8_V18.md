# Point 8 — Loan Terms & Conditions (V18)

Implemented on top of `final_cam_collateral_point7_v17.zip`.

## Backend
- Added `app/cam/loan_terms/service.py` and package export.
- Added `GET /api/cam/loan-terms/<session_id>` with cache / `?refresh=1`.
- Added `PUT /api/cam/loan-terms/<session_id>` for explicit credit-officer overrides.
- Reuses Point 4 Financial Analysis, Point 5 Credit History, Point 6 Risk Assessment and Point 7 Collateral outputs.
- Deterministic requested-vs-proposed-vs-policy comparison and POC policy-constrained tenor/moratorium/amount.
- Deterministic covenants, pre-disbursement conditions, post-disbursement monitoring and deviations.
- Pricing values are never invented; they are shown only if present in proposal/pricing data.
- Groq is used only to phrase the final CAM commentary from structured facts.
- Background CAM processing now prepares Loan Terms after Collateral.

## Frontend
- Replaced Point-8 placeholder in `Step10.js` with full BOB-style Loan Terms screen.
- Added KPI row, Facility Structure, Requested vs Proposed vs Policy, Pricing, Repayment, Security, Covenants, Pre/Post Conditions, Deviations and AI commentary.
- Added Edit / Update flow for facility type, proposed amount, tenor, moratorium, interest rate and repayment.
- Added responsive styling in `globals.css`.

## Policy note
Thresholds in V18 are POC defaults only. Production must source approved thresholds from the Policy module / product program.
