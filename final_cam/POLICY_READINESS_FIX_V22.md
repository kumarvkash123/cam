# CAM vs Policy Readiness Fix V22

## Problem fixed
After a policy upload, CAM vs Policy Analysis could remain disabled because the frontend only treated `analysis_completed` as complete. A CAM whose status had advanced to `completed` (for example after final CAM generation) was incorrectly shown as `In Analysis`, even though the backend accepted it.

## Changes
- Normalized CAM completion: both `analysis_completed` and `completed` are valid terminal states.
- Added backend `can_run_policy_analysis`, `cam_analysis_complete`, `missing_cam_sections`, `reason`, and `message` readiness fields.
- Policy-analysis POST now uses backend readiness as the single gate instead of duplicating raw status logic.
- Added a CAM snapshot hash to policy-analysis results so policy analysis becomes stale if CAM inputs/results change.
- Existing policy analyses without a CAM snapshot are marked for a one-time refresh.
- Policy hash continues to invalidate analysis when a policy is uploaded/changed.
- CAM vs Policy UI now enables Run/Re-run from backend readiness, shows the exact reason when blocked, and lists pending CAM sections when applicable.
- Final CAM Review and Generate CAM re-check policy readiness rather than trusting stale frontend state.

## Resulting flow
CAM complete + active policy -> Run CAM vs Policy Analysis enabled.
CAM changed -> Re-run required.
Policy changed -> Re-run required.
CAM incomplete -> Run disabled with pending section details.
Current analysis -> Final CAM Review / Generate CAM enabled.
