# V15 — CAM Point 5: Credit History & Repayment Track Record

Implemented on top of V14.

## Backend
- Added `app/cam/credit_history/`.
- Added `GET /api/cam/credit-history/<session_id>` and `?refresh=1`.
- Normalizes bureau, internal banking and uploaded-document evidence.
- Deterministically calculates repayment summary, DPD, facility exposure and utilisation rules.
- Distinguishes missing evidence from a clear/no-adverse result.
- Groq is used only for narrative wording; it does not calculate credit metrics.

## Frontend
- Rebuilt Step 9 as the Point-5 BOB-style dashboard.
- Added KPI cards, lender facilities, repayment track, banking conduct, bureau summary, utilisation checks, risk flags, evidence and AI commentary.
- Because the existing application intentionally combines CAM Points 5 and 6 in workflow Step 9, the Next button switches to the retained Risk Assessment & Mitigation sub-view before continuing to Collateral & Loan Terms.
