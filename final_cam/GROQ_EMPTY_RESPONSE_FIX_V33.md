# Groq Empty Loan Summary Fix V33

## Root cause handled
The V32 gateway accepted HTTP 200 responses and returned `choices[0].message.content` without validating that the final content was non-empty. GPT-OSS is a reasoning model and Groq can return reasoning separately from final content.

## Changes
- GPT-OSS requests explicitly send `include_reasoning=false`.
- GPT-OSS requests use `reasoning_effort=low` for CAM narrative calls.
- Added `max_completion_tokens=1400`.
- Added `[GROQ-RAW-DEBUG]` request/response metadata logs without logging the API key or full CAM prompt.
- Validates final assistant `content`.
- HTTP 200 + empty content triggers exactly one controlled retry with a smaller 10,000-character request budget and an explicit final-answer instruction.
- If the retry is also empty, the gateway raises a clear `LLMGatewayError` instead of silently returning an empty string.
- Existing 413 and 429 handling remains intact.

## Debug lines to share
Search the Flask console for:

```
[GROQ-RAW-DEBUG] request
[GROQ-RAW-DEBUG] response
[GROQ-RAW-DEBUG] empty_content_retry
[GROQ-RAW-DEBUG] empty_content_retry_success
[CAM-LS-DEBUG] groq_output
```

A normal successful call should show `status=200` and `content_length` greater than zero.
