# Generate CAM Gate Fix V24

## Problem
The Generate CAM screen used `/api/cam/policy-readiness/<session_id>` and correctly showed CAM Analysis = Complete / READY when every required analytical stage (including Point 9) was completed. However, the backend `generate_cam()` function still used the legacy session-level `state.status` gate. A session could therefore be stage-complete while `state.status` still remained `in_analysis`, producing the contradictory error `Complete CAM analysis before generating the CAM`.

## Fix
- `generate_cam()` now uses `policy_engine.readiness(state)` as the same single source of truth used by Final Review and Generate CAM UI.
- Generation now checks `cam_analysis_complete` from the required stage map rather than the legacy top-level status.
- Missing CAM sections are returned explicitly when generation is genuinely blocked.
- The latest CAM-vs-policy analysis must still be current; policy hash and CAM snapshot freshness remain enforced.
- The frontend clears stale generation errors before a new attempt and again after successful generation.

## Result
When the Generate CAM page says CAM Analysis = Complete, Policy Freshness = Current and readiness = READY, the backend now accepts the same readiness decision and generates the final DOCX (and PDF when LibreOffice is available).
