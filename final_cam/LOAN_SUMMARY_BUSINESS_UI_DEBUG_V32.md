# Loan Summary Business UI + Debug V32

## What changed
- Executive Credit Summary now shows borrower/MCA identity, proposal snapshot, concise Groq narrative, deterministic strengths, attention items, pending information and source badges.
- Groq prompt is shortened to 90–130 words / 3–5 sentences and is narrative-only.
- Revenue & PAT card retains the 3-year chart and adds a deterministic trend insight.
- Recent Activities is replaced by Verification & Data Status.
- CAM Data Readiness is separate from raw document-processing readiness.
- Credit & Banking supports clearly-labelled Synthetic POC data for Lactose where genuine bureau/internal-bank data is unavailable.
- Risks & Mitigants are derived from calculated metrics/rules before Groq presentation.
- Collateral card can show the POC synthetic valuation and calculated coverage, clearly labelled synthetic.
- Compliance uses Verified / Pending / Review / Exception states instead of generic Not Available.
- Public Information supports a clearly-labelled Lactose POC public-reference block; refresh from live sources before credit use.

## Debugging
Two searchable log prefixes are retained/enabled by default:

- `[CAM-FIN-DEBUG]` — annual-report selection, raw financial rows, unit normalization, calculations and final financial payload.
- `[CAM-LS-DEBUG]` — proposal, borrower, credit/banking, risk, collateral, compliance, public info, readiness, presentation model, Groq input context and Groq output.

Disable with:

```powershell
$env:CAM_FINANCIAL_DEBUG="0"
$env:CAM_LOAN_SUMMARY_DEBUG="0"
```

For troubleshooting, send logs from `[CAM-LS-DEBUG] presentation_context` through `[CAM-LS-DEBUG] groq_output`, plus `[CAM-FIN-DEBUG] selected_annual_report` and `normalized_structured_metrics`.

## Safety/source rule
Synthetic POC private verification is never labelled as real API verification. Missing KYC/sanctions/PEP results remain pending rather than being fabricated.
