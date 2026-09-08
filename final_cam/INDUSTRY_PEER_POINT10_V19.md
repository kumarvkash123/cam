# V19 — Point 10 dependency and UI update

Processing dependency is now:

1 → 2 → 3 → 4 → 5 → 6A → 7 → 10 → 6B final consolidated risk → 8 → 9.

Point 10 is implemented by `app.cam.industry_peer` and `/api/cam/industry-peer/<session_id>`.
It consumes Business Overview, Financial Analysis, the configured industry/peer provider and public-search feed.
Missing peer metrics remain unavailable; the LLM may phrase commentary but cannot invent peer values.

Point 7 now navigates to the Point 10 screen before Point 8. Point 10 then routes the user to Loan Terms & Conditions.
