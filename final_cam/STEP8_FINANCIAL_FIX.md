# Step 8 Financial Analysis Fix

## Problem fixed
The previous Step 8 rendered the complete CAM analysis pipeline (`analysis.steps`) inside the Financial Analysis screen. This duplicated Loan Summary, Borrower Information, Business Overview and other reports that already have dedicated workflow pages.

## New behavior
Step 8 now selects only the `financial_analysis` report and renders a dedicated Financial Analysis & Stress Testing UI containing:
- Borrower / CAM banner
- Financial trends
- Key ratios
- Financial highlights
- Grounded financial insights
- Deterministic POC stress-testing scenarios
- Financial credit-evaluation summary
- Proceed to Credit History navigation

The workflow-level CAM processing remains initiated from Step 4 (CAM Readiness & Start Analysis).

## Backend payload
`backend/app/cam/report_builder.py` now adds a structured `data` object to the Financial Analysis report with:
- `years`
- `trends`
- `ratios`
- `highlights`
- `insights`
- `stress_testing`
- `credit_evaluation`

The existing `sections` payload is retained for backward compatibility.

## Validation
- All 30 frontend JS/JSX files passed TypeScript JSX syntax transpilation.
- Backend `report_builder.py` passed Python byte-code compilation.
- Confirmed Step8 contains no `analysis.steps` loop and no `ReportStep` rendering.
