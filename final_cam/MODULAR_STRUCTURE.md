# CAM Modular Structure

## Frontend

All CAM UI code is under `frontend/modules/cam/`.

- `CAMWorkspace.js` – coordinator, shared CAM state/actions, shell.
- `steps/Step1.js` … `steps/Step14.js` – each CAM journey page is separated into its own file.
- `ReportStep.js` – report rendering support.
- `api.js` – frontend API helper.
- `constants.js` – CAM constants.

The previous ~4,940-line CAM page is no longer one monolithic render file.

## Backend

CAM backend code is under `backend/app/cam/`. HTTP routes are separated by responsibility:

- `route_handlers/session_routes.py` – start CAM and CAM assistant
- `route_handlers/policy_routes.py` – policy upload/list/chat
- `route_handlers/document_routes.py` – document upload/list/chat
- `route_handlers/mca_routes.py` – MCA fetch/status
- `route_handlers/analysis_routes.py` – analysis, reports, status, loan summary
- `route_handlers/generation_routes.py` – template, generation and downloads
- `routes.py` – only registers the route modules
- `blueprint.py` – shared Flask blueprint

Existing `/api/cam/...` URLs are preserved.
