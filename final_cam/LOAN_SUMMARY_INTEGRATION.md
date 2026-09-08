# Loan Summary POC Integration (v6)

## Existing flow preserved
1. Borrower Details
2. Document Upload
3. Document Review & Mapping
4. CAM Readiness & Start Analysis
5. Loan Summary
6-15. Remaining CAM workflow

No step was removed or renumbered. Step 5 now calls a dedicated Loan Summary API and no longer tries to assemble all evidence in the browser.

## Step 5 API
`GET /api/cam/loan-summary/<session_id>`

Use `?refresh=1` to rebuild the summary after inputs change. The backend keeps a session cache for normal revisit/navigation.

## Data pipeline
Reviewed uploaded PDFs -> existing extraction/normalization -> deterministic financial metrics/rules

Existing MCA/FileSure state + mock/live external providers -> normalized external data

Mock/Google public search -> material public-information context

All of the above -> `loan_summary_context` (small structured JSON) -> Groq narrative only

Groq does not receive raw PDFs and does not calculate financial ratios or make sanction decisions.

## New backend modules
- `app/cam/loan_summary_service/mock_provider.py` - finds one of the five packaged synthetic companies and loads JSON responses.
- `app/cam/loan_summary_service/external_data_service.py` - switches between `mock`, `hybrid`, and `live` modes.
- `app/cam/loan_summary_service/public_search_service.py` - switches public enrichment between `mock`, `google`, and `off`.
- `app/cam/loan_summary_service/context_builder.py` - merges proposal, documents, MCA/APIs, deterministic outputs, risk/collateral/compliance, and public information into one bounded context.
- `app/cam/loan_summary.py` - retains the existing extraction/rule helpers but now builds the enriched Step-5 response through the new services.
- `app/cam/llm_service.py` - Groq prompt now receives only normalized Loan Summary context and is explicitly prohibited from originating calculations/facts or sanction decisions.

## Packaged synthetic data
`backend/demo_data/loan_summary/`

Five companies are included:
- Sunrise Engineering Pvt. Ltd.
- Bell Flower Trading Co. Pvt. Ltd.
- GreenLeaf Foods Pvt. Ltd.
- Apex Auto Components Pvt. Ltd.
- Nova Textiles Pvt. Ltd.

Each company includes uploadable PDFs, mock MCA/GST/PAN/Udyam/Bureau/Banking/Screening/Industry/Proposal JSON, derived financial/risk/compliance JSON, and synthetic public company-news/rating/industry/adverse-media JSON.

## Environment switches
```env
CAM_DATA_MODE=mock
PUBLIC_SEARCH_MODE=mock
```

For live Google search:
```env
PUBLIC_SEARCH_MODE=google
GOOGLE_API_KEY=<key>
GOOGLE_CSE_ID=<programmable-search-engine-id>
```

For real/state data with no synthetic fallback:
```env
CAM_DATA_MODE=live
```

For a mixed POC where real MCA can override the mock MCA but the other demo feeds are retained:
```env
CAM_DATA_MODE=hybrid
```

## Frontend Step 5
`frontend/modules/cam/steps/Step5.js` now shows:
- Borrower/source banner
- Loan Proposal
- Key Financial Indicators
- Executive Credit Summary
- Credit & Banking snapshot
- Major Risks & Mitigants
- Collateral Highlights
- Compliance Snapshot
- Public Information (rating, recent developments, industry/adverse media)
- Existing CAM Assistant

A Refresh Summary button calls the same API with `?refresh=1`.

## Source precedence
1. User/session proposal values
2. Reviewed/extracted document data
3. Real/state MCA when using live/hybrid mode
4. Matching mock external API data in POC mode to fill missing values
5. Public-search information only as supporting context
6. Groq only narrates the bounded context

## Validation performed
- Backend Python modules compile with `python -m compileall`.
- Updated `Step5.js` and `CAMWorkspace.js` pass JavaScript syntax checking.
- Duplicate `setMcaStatus` declaration in `CAMWorkspace.js` was removed during this integration audit.
- All five mock companies were checked for required external/public JSON files.
- Full Flask runtime integration could not be executed in the artifact environment because Flask is not installed there; run the included project requirements locally before starting the backend.
