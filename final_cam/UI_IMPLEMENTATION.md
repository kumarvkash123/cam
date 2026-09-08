# Bank of Baroda CAM UI Implementation

The Next.js frontend now uses a Bank of Baroda themed CAM journey with 15 screens.

1. Select / Create Borrower
2. Documents Center
3. Document Review & Data Mapping
4. CAM Readiness / Start CAM
5. Loan Summary
6. Borrower Information
7. Business Overview
8. Financial Analysis & Stress Testing
9. Credit History & Risk Assessment
10. Collateral & Loan Terms
11. Compliance Checks
12. Industry Overview, Peer Benchmarking & Market Analysis
13. Final CAM Review
14. Policy Document Management & AI Copilot
15. CAM vs Policy Analysis

The existing Flask APIs and CAM processing functions are retained. The new UI calls the existing endpoints for CAM creation, CAM Assistant, policy upload/indexing, policy RAG chat, borrower document processing, borrower document chat, MCA fetch, CAM analysis/status, final CAM generation, and DOCX/PDF download.

The process sidebar is collapsed by default on large screens and expands on demand.
