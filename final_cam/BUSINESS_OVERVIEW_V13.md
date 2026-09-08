# Business Overview V13

Implemented Point 3: Business Overview as a source-grounded CAM section.

## Backend
- Added `app/cam/business_overview/` with `service.py` and `ai_enrichment.py`.
- New API: `GET /api/cam/business-overview/<session_id>` and `?refresh=1`.
- Reuses Borrower Information, uploaded document extraction, financial trends, external/mock APIs, MCA state and public-search feed.
- Calculates revenue growth/CAGR deterministically from available financial evidence.
- Groq receives only normalized Business Overview context and generates the narrative; it is not allowed to invent products, customers, market share, locations, capacity or financial values.
- Background CAM pipeline prepares Step 7 after Step 6 and caches it.
- Final CAM report builder uses the enriched Business Overview cache when available.

## Frontend
- Rebuilt Step 7 in BOB style.
- Added Business Model, Products/Services, Customer Profile, Operating Footprint, Revenue/PAT Trend, Market Position, Strengths/Risks, Recent Developments, AI Business Overview, source strip and a single Copilot drawer.
- Multi-year graph uses deterministic financial trend data and does not use Groq for values.

## Source priority
1. Reviewed uploaded documents
2. Bank/internal CAM data
3. MCA / official APIs
4. Annual report / company disclosures / website when available
5. Public search
6. Synthetic POC provider as fallback
7. Groq only for extraction/synthesis/narrative

Missing business facts are shown as unavailable rather than estimated.
