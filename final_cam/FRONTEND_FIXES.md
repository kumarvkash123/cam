# Frontend Fixes Applied

1. Fixed `ReferenceError: API is not defined` in `modules/cam/steps/Step3.js` by importing the shared `API_BASE` from `modules/cam/api.js`.
2. Fixed the same undefined API reference in `modules/cam/steps/Step13.js` for CAM DOCX/PDF download links.
3. Split Step 15 out of `Step14.js` into `modules/cam/steps/Step15.js`.
4. Removed the invalid second top-level `return` from `Step14.js` that caused `Return statement is not allowed here`.
5. Added the missing Step 15 import in `CAMWorkspace.js`.
6. Added Step 15 to the workspace step-component render map, so `journeyStep === 15` renders correctly.
7. Verified all frontend relative imports resolve to existing source files.
8. Verified CAM API references now have a declaration/import.
9. Preserved the earlier backend classifier/OCR fixes in this package.

Frontend API configuration remains centralized at `frontend/modules/cam/api.js` using `NEXT_PUBLIC_API_BASE_URL` with the existing default `http://localhost:8000`.
