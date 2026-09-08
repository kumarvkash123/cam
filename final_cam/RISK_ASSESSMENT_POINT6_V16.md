# V16 — CAM Point 6: Risk Assessment & Mitigation

Implemented on top of V15.

## Backend
- Added `app/cam/risk_assessment/` with deterministic risk consolidation.
- Reuses Financial Analysis, Credit History and Business Overview caches.
- Adds policy/threshold comparison, risk register, mitigation catalogue, category scoring, likelihood/impact matrix and human-decision notice.
- Added `GET /api/cam/risk-assessment/<session_id>` and `?refresh=1`.
- Background CAM analysis now prepares Point 5 and Point 6 caches after Point 4.
- Groq is used only to phrase the deterministic risk narrative.

## Frontend
- Replaced the old Point-6 placeholder in `Step9.js`.
- Added `frontend/modules/cam/risk-assessment/components.js`.
- Added BOB-style overall risk card, category summary, risk matrix, risk/mitigation register, threshold table, positive factors, concerns and AI commentary.
- Preserved existing Point 5 -> Point 6 -> Collateral navigation.

## Control note
The risk score is decision-support only. Unavailable categories are explicitly `Not Assessed` and excluded from the overall score. Final credit judgement and sanction conditions remain human-controlled.
