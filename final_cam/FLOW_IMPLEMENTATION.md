# Corrected CAM Flow Implementation

This package implements the agreed 15-step CAM journey:

1. Borrower Details
2. Document Upload
3. Document Review & Mapping
4. CAM Readiness & Start Analysis
5. Loan Summary
6. Borrower Information
7. Business Overview
8. Financial Analysis & Stress Testing
9. Credit History & Risk Assessment
10. Collateral & Loan Terms
11. Compliance Checks
12. Industry & Peer Analysis
13. Policy Management
14. CAM vs Policy Analysis
15. Final CAM Review

## Flow corrections

- CAM analysis now starts from Step 4 instead of Step 8.
- Missing optional proposal fields remain warnings; they do not block analysis.
- Step 8 can re-run analysis, but is no longer the primary start point.
- Policy Management now comes before CAM-vs-Policy analysis.
- CAM-vs-Policy review must be completed before Final CAM generation.
- Final Review now tracks the bank-required 10 CAM report sections rather than workflow setup screens.
- Credit History/Risk and Collateral/Loan Terms remain combined UI screens but map to separate CAM report sections.
- Backend records a human policy-review gate and blocks final CAM generation until that gate is complete.

## Backend addition

POST /api/cam/policy-review/<session_id>

Records the human policy-review completion after CAM analysis and policy indexing.
