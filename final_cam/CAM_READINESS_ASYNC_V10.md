# CAM Readiness + async Loan Summary flow (v10)

- Step 4 is now a BOB-style readiness dashboard with deterministic weighted checklist, key documents, readiness donut, missing/pending items and mandatory/recommended distinction.
- `GET /api/cam/readiness/<session_id>` supplies Step-4 readiness data.
- Clicking Start CAM no longer navigates directly to Step 5.
- The existing Flask background analysis thread prepares the Loan Summary first. Status exposes `analysis_stages`, `loan_summary_ready`, and `loan_summary_error`.
- Step 4 polls the existing status endpoint and remains in a preparation/progress view.
- Step 5 opens only after a successful Groq executive summary and a valid Loan Summary payload are available.
- If Groq fails, Step 4 shows the actual error and a Retry Groq action; no deterministic narrative fallback is used.
- Once Loan Summary is ready, remaining CAM report/narrative generation continues in the background.
- Missing optional proposal/collateral/credit items are warnings. At least one supporting document remains the current minimum backend requirement to start analysis.
