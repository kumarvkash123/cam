# CAM Synthetic Loan Summary Dataset v1

All files in this package are synthetic/demo data. They do not represent real customers, real tax filings, real bureau results, or real bank records.

## Purpose
This dataset is designed to test Step 5 - Loan Summary end to end:
Document Upload/OCR -> normalization -> deterministic financial metrics -> mock external APIs -> risk/compliance -> limited Loan Summary context -> Groq narrative.

## Companies
1. Sunrise Engineering Pvt. Ltd. - lower-risk manufacturing case
2. Bell Flower Trading Co. Pvt. Ltd. - moderate-risk trading case
3. GreenLeaf Foods Pvt. Ltd. - stronger food-processing case
4. Apex Auto Components Pvt. Ltd. - leveraged but performing manufacturing case
5. Nova Textiles Pvt. Ltd. - stressed/watchlist textile case

## Per-company uploadable PDFs
01 Loan Proposal Form
02 Audited Financial Statements
03 Bank Statement Summary
04 ITR Computation
05 GST Returns Summary
06 Shareholding & Management
07 Collateral Valuation Report
08 Credit Bureau Report
09 Projected Financials
10 KYC & Registration Pack

## Per-company mock API JSON
mca_response.json
gst_response.json
pan_response.json
udyam_response.json
bureau_response.json
internal_banking_response.json
sanctions_screening_response.json
industry_peer_response.json
loan_proposal.json

## Derived / engine JSON
computed_financial_metrics.json
risk_engine_output.json
compliance_engine_output.json
loan_summary_context.json
expected_loan_summary_output.json

## Common policy PDFs
Synthetic_MSME_Credit_Policy.pdf
Synthetic_Collateral_Policy.pdf

The intended production rule is: Groq receives loan_summary_context.json only, not all raw PDFs or the full CAM state.
