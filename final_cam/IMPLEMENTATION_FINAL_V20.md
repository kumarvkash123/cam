# Final implementation — Document Preview + CAM Workflow Sidebar

Implemented on the uploaded `final_cam(2).zip` codebase.

## Document preview fix
- Local storage is now anchored to `backend/storage`, independent of the folder used to start Flask.
- Added backward-compatible path resolution for existing DB rows containing `./storage`, Windows backslashes, mixed separators, and absolute paths.
- Preview endpoint now resolves legacy/current paths, sets the correct MIME type, serves inline, disables unsafe content-type sniffing, and returns a clear 404 when the physical file is genuinely missing.
- Delete and classification-confirm flows use the same resolver.
- Document Review now pre-checks preview availability and shows loading/error/retry/re-upload states instead of rendering raw backend errors in the iframe.

## Sidebar / workflow
The sidebar follows the reference visual style but uses the bank workflow order:

1 → 2 → 3 → 4 → 5 → 6A → 7 → 10 → 6B → 8 → 9 → Policy Analysis → Final CAM Review

- CAM Analysis can expand/collapse independently from the whole sidebar.
- Active analysis rows use the BOB orange state and white section badge.
- Business section numbering is intentionally independent of internal React step numbers.
- Workflow mapping lives in `frontend/modules/cam/config/camWorkflow.js`.
- Sidebar component lives in `frontend/modules/cam/components/CAMSidebar.js`.

## 6A / 6B split
- 6A is now an assessment view: risk identification, severity, matrix, threshold comparison and concerns.
- Point 7 Collateral follows 6A.
- Point 10 Industry / Peer follows Point 7.
- Point 10 invalidates the cached consolidated risk view on the backend.
- 6B reloads risk after Point 10 so collateral + industry/peer context feed the final mitigation plan.
- Point 8 Loan Terms follows 6B.
- Point 9 Regulatory & Compliance follows Point 8.

## Validation performed
- Python compileall: passed for `backend/app`.
- Legacy document resolver checked against existing `kyc_poc.db` records and bundled storage files: resolved successfully.
- Changed JavaScript/JSX modules parsed successfully with Next's bundled Babel parser.
- Full `next build` could not complete in the isolated build environment because Next attempted to download the Linux SWC binary from npm and outbound network access is unavailable. This is an environment limitation, not a reported source parse error.

## Run
Backend: use the same command/environment as your current project. The new storage resolver no longer depends on the working directory.

Frontend:

```bash
cd frontend
npm install
npm run dev
```
