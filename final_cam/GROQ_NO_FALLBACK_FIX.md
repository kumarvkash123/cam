# Groq Executive Summary — No Silent Fallback Fix (v8)

## Problem fixed
The previous Step 5 initialized `executive_summary` with a deterministic template. If Groq was unavailable or failed, that template was still displayed and the page showed `Deterministic Fallback`. This could make a failed Groq path look like a valid generated Loan Summary.

## New behavior
- Step 5 Executive Credit Summary is displayed only when `summary_source == "ai_generated"`.
- Missing key, import error, provider error, empty response, or unexpected error returns `summary_source = "groq_failed"` and `executive_summary = null`.
- UI shows the Groq status/model/error and a **Retry Groq** button instead of fabricated/fallback narrative.
- Failed Groq attempts are **not cached**. Only a successful AI-generated summary is cached.
- After fixing `.env`, model, connectivity, etc., reopening Step 5 or clicking Retry Groq makes a fresh Groq attempt.

## Files changed
- `backend/app/cam/loan_summary.py`
- `backend/app/cam/route_handlers/analysis_routes.py`
- `frontend/modules/cam/steps/Step5.js`

## Expected successful state
- Badge: `Groq AI Draft`
- `summary_source`: `ai_generated`
- `llm_status.status`: `success`

## Expected failed state
- Badge: `Groq Required`
- No Executive Credit Summary text is substituted.
- The exact Groq error is shown with Retry Groq.
