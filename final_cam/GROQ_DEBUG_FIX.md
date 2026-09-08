# Groq Loan Summary Debug Fix

## Root issue found
`backend/app/cam/loan_summary.py` silently swallowed every Groq exception:

```python
except (LLMGatewayError, Exception):
    pass
```

Therefore any missing key, invalid model, HTTP error, network failure, import failure, or empty response silently changed the UI to `Deterministic Fallback` with no reason shown.

The distributed ZIP intentionally contains `.env.example`, not a real `.env`, so a local `backend/.env` with `GROQ_API_KEY` is still required.

## Changes
- Added explicit Groq status/error information to the Loan Summary API response (`llm_status`).
- Added backend logging for start/success/provider/unexpected errors.
- Added visible Step 5 diagnostics when fallback is used.
- Added `Retry Groq` button; it calls the existing `?refresh=1` endpoint so a cached fallback is rebuilt.
- Preserved deterministic fallback so Step 5 never breaks if Groq is unavailable.

## Local configuration
Create `backend/.env` from `.env.example` and set:

```env
GROQ_API_KEY=your_real_key
GROQ_MODEL=openai/gpt-oss-120b
```

Restart Flask after editing `.env`, then click `Retry Groq` / `Refresh Summary`.

When successful, the Step 5 badge changes from `Deterministic Fallback` to `Groq AI Draft` and `llm_status.status` is `success`.
