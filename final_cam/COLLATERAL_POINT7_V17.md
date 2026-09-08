# CAM Point 7 — Collateral Details (V17)

Implemented on top of V16 Risk Assessment.

## Backend
- Added `app/cam/collateral/service.py` and package export.
- Added `GET /api/cam/collateral/<session_id>` with `?refresh=1` support and per-session cache.
- Sources: structured proposal/security data, extracted valuation/title/legal/insurance/charge fields, uploaded document metadata and available MCA charge evidence.
- Deterministic: value normalization, valuation age, eligible-value aggregation, coverage ratio, ownership/title/charge/insurance checks, document completeness and observations.
- Missing evidence remains `Not available` / `Not verified` rather than being treated as clear.
- Groq is used only to phrase a bounded collateral commentary from structured facts.
- Background CAM analysis now prepares Point 7 and invalidates Point 6 risk cache so collateral findings can be included when Risk Assessment is revisited.
- Risk Assessment now consumes `collateral_cache` and can add collateral coverage, valuation-age and verification risks.

## Frontend
- Replaced the old collateral placeholder in Step 10 with the Point-7 BOB dashboard.
- Added KPI cards, security details, valuation table, coverage analysis, ownership/charge validation, document checklist, key observations, AI commentary and evidence/methodology.
- Preserved the combined workflow screen: Point 7 -> Point 8 Loan Terms -> Compliance.

## Important POC note
The default collateral coverage threshold (1.50x) is a configurable POC threshold only unless supplied by state/policy. It must be replaced by product-specific bank policy rules for production.
