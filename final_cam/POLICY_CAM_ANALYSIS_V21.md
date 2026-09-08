# Policy Management + CAM vs Policy Analysis V21

Implemented on top of `final_cam_v20_final`.

## Workflow
Documents Center -> Document Review -> CAM Analysis (1,2,3,4,5,6A,7,10,6B,8,9) -> Policy Documents -> CAM vs Policy Analysis -> Final CAM Review -> Generate CAM.

## Added
- Separate top-level sidebar entries for Policy Documents, CAM vs Policy Analysis, Final CAM Review and Generate CAM.
- Synthetic MSME policy set with 44 normalized policy rules for the POC.
- Active-policy metadata/version/hash handling and policy freshness checks.
- Policy upload invalidates stale policy analysis and marks the uploaded policy as active metadata while synthetic normalized rules remain the POC rule source.
- Policy readiness API and deterministic CAM-vs-policy analysis API.
- Company/CAM/loan/status filters and Run/Re-run CAM vs Policy Analysis action.
- Overall compliance, category compliance, CAM draft vs policy table, deviations, policy sources, analysis history and copilot UI.
- Final review gating and dedicated Generate CAM page.
- Final CAM generation re-checks policy freshness server-side.
- Synthetic policy data is also available to Policy Copilot when no uploaded policy file exists.

## New APIs
- GET `/api/cam/policy-active/<session_id>`
- GET `/api/cam/policy-readiness/<session_id>`
- GET/POST `/api/cam/policy-analysis/<session_id>`
- GET `/api/cam/policy-history/<session_id>`

## POC note
Synthetic rules are intentionally normalized/deterministic. Uploaded files update the active-policy version/hash and are available for RAG Q&A. A later production phase should add policy-rule extraction + human approval before uploaded rules replace the synthetic normalized rules.
