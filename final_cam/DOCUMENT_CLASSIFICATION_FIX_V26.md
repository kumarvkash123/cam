# Document Classification Fix V26

This change fixes the document-type errors observed in the generated CAM source register.

## Newly supported document types
- `loan_application`
- `stock_statement`
- `annual_return_mgt7`
- `shareholding_pattern`
- `secretarial_compliance`
- `audited_financial_results`

## Classification improvements
1. The classifier now accepts the original filename as evidence in addition to extracted text/layout.
2. Filename evidence is additive, not a blind hard override; document text still contributes to the score.
3. Strong negative signals separate confusable documents such as Loan Application vs ITR and Stock Statement vs Bank Statement.
4. Existing Annual Report, Bank Statement and ITR types now also use filename evidence.

## Expected Lactose test classifications
- `02_loan_application_synthetic.pdf` -> Loan Application / Proposal
- `05_bank_statement_12_months_synthetic.pdf` -> Bank Statement
- `08_stock_and_debtors_statement_synthetic.pdf` -> Stock & Debtors Statement
- `Annual_Report_-_2024.pdf` -> Annual Report
- `Annual_Report_-_2025.pdf` -> Annual Report
- `Annual_Report_2025-26.pdf` -> Annual Report
- `Annual_Secretarial_Compliance_Report_-_2024.pdf` -> Secretarial Compliance Report
- `Audited_Financial_Report_for_Quarter_and_Year_Ended_as_on_31st_March_2025.pdf` -> Audited Financial Results
- `MGT-7_Annual_Return_F.Y._2023-24.pdf` -> Annual Return (MGT-7)
- `Shareholding_Pattern_as_on_31st_March_2026.pdf` -> Shareholding Pattern

## Important
Existing database rows keep their old classification. Re-upload the documents into a new CAM session, or use the existing manual correction endpoint, to see the corrected types.
