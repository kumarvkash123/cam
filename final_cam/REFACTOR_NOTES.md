# CAM AI Platform Refactor

## Changes implemented

### Frontend state
- Added Redux Toolkit and React Redux.
- `authSlice` manages the logged-in user in application state.
- `camSlice` manages shared CAM workflow state: CAM/session IDs, borrower, documents, policy state, MCA, analysis, chats and generation state.
- `File` objects and transient UI state remain in local React state.
- `localStorage` / `sessionStorage` is retained only for login persistence (`bob_cam_user`); it is not used as the CAM state store.

### Frontend structure
- `app/page.js` is now the application shell.
- `components/auth/LoginPage.js` contains login UI.
- `components/dashboard/Dashboard.js` contains dashboard UI.
- `components/dashboard/widgets.js` contains dashboard widgets.
- `components/layout/Sidebar.js` contains dashboard navigation.
- `components/cam/CAMWorkspace.js` contains the CAM workflow.
- `components/cam/ReportStep.js` contains report-step rendering.
- `components/ui.js` contains shared visual helpers and assistant response rendering.
- `store/` contains Redux store and slices.

### Groq response quality
- Added `backend/app/response_formatter.py`.
- General CAM Assistant prompt explicitly forbids JSON, Python dictionaries, raw context/evidence dumps and internal prompt leakage.
- Policy/document RAG prompt uses the same human-readable Markdown contract.
- Accidental JSON responses are converted into readable Markdown as a backend safety net.
- Frontend assistant messages render headings, bullets, numbered items and basic bold Markdown instead of showing raw formatting syntax.

## Runtime model

Backend CAM session/database remains the source of truth. Redux is the frontend runtime state/cache. Browser storage is only for login persistence.

## Installation

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Production build:

```bash
npm run build
npm start
```

Backend:

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Make sure `backend/.env` contains the required Groq and other service configuration.

## Modular Flask + Groq payload protection (2026-09-06)

- `backend/app.py` is now a thin entry point (11 lines).
- Flask application creation moved to `backend/app/factory.py`.
- API routes are split into `main_routes.py`, `cam_routes.py`, and `applications_routes.py` using Blueprints.
- Shared CAM/business helpers are in `backend/app/core.py`.
- Added `backend/app/llm_gateway.py` as the single size-aware Groq client.
- RAG and CAM narrative generation now use the gateway instead of calling Groq directly.
- The gateway limits complete request size, limits history, and performs one smaller retry on HTTP 413.
- CAM evidence is bounded before JSON serialization; RAG sends only retrieved excerpts.
- Raw provider exceptions are no longer returned to the UI.
- Runtime files (`storage`, generated `output`, local DB, `.env`) should not be committed to source control.
