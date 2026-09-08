# Final CAM BOB changes

## Document Review & Data Mapping
- Bank of Baroda navy/orange styling.
- Document preview and full-screen preview.
- Extracted field mapping with confidence and status.
- Document details and validation checks.
- Approve & Proceed, Send for Rework and Discard actions.

## CAM Analysis validation fix
The previous `/api/cam/analyze/<session_id>` endpoint rejected the request when Loan Type,
Loan Amount, Purpose, Tenure, Interest Rate or Repayment was not captured. The validation is
now non-blocking. Missing conversational fields are recorded in `analysis_missing_inputs` and
the analysis proceeds when the CAM session/application and at least one document are available.

The UI explicitly tells the credit officer that missing proposal fields can be captured later
through CAM Assistant and will remain `Not available` until captured.

## General Borrower + Web CAM Assistant

- Replaced the forced Loan Type → Amount → Purpose → Tenure → Interest → Repayment chatbot sequence on Loan Summary.
- Loan Summary CAM Assistant now accepts free-form questions at any time.
- Added backend Google Programmable Search integration (`GOOGLE_API_KEY` + `GOOGLE_CSE_ID`).
- Added Groq-powered response generation using borrower/CAM context, uploaded-document evidence, MCA data, and Google search results.
- Search credentials and Groq credentials remain server-side in `backend/.env`.
- The assistant can opportunistically capture proposal fields when a user mentions them, without forcing a sequence.
- Added web/document source links to the active Loan Summary chatbot.
