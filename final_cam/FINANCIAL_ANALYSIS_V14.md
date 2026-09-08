# V14 — Point 4 Financial Analysis & Stress Testing

Implemented on top of `final_cam_business_overview_v13.zip`.

## Frontend
- Replaced Step 8 with the Bank of Baroda Financial Analysis & Stress Testing dashboard.
- KPI cards: Revenue, EBITDA, PAT, Net Worth, Total Debt.
- Financial ratio table with configurable benchmark/status display.
- Multi-period Revenue/EBITDA/PAT chart with no additional npm chart dependency.
- Material movement analysis.
- Base / Moderate / Severe stress testing table.
- AI/Rule commentary card, source evidence strip, refresh and previous/next navigation.
- Responsive BOB styling added to `app/globals.css`.

## Backend
- Added modular `app/cam/financial_analysis/` service.
- Ratios, movement calculations, benchmark checks and stress scenarios are deterministic Python calculations.
- Groq is optional and only phrases calculated facts; it is not the source of any number.
- Added `GET /api/cam/financial-analysis/<session_id>` with `?refresh=1` support.
- Financial analysis is also prepared/cached during background CAM analysis.

## Notes
- Benchmark values are POC defaults in `financial_analysis/service.py` and should be replaced/loaded from the bank policy engine for production.
- Stress assumptions are explicit POC scenarios and are not a credit decision.
