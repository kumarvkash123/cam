# Financial Debug Trace V30

This build adds an explicit financial-pipeline debugger for the Loan Summary.

## Enable / disable

Enabled by default for the POC. To disable:

```powershell
$env:CAM_FINANCIAL_DEBUG="0"
```

To enable explicitly:

```powershell
$env:CAM_FINANCIAL_DEBUG="1"
```

Restart the Flask backend after changing the environment variable.

## What gets printed

Search the backend console for:

```text
[CAM-FIN-DEBUG]
```

The main stages are:

1. `annual_report_candidate`
2. `selected_annual_report`
3. `normalized_structured_metrics`
4. `financial_path`
5. `loan_summary_context_financials`
6. `final_loan_summary_financial_payload`

On Windows PowerShell you can capture the backend output and filter it with `Select-String "CAM-FIN-DEBUG"`.

## API debug payload

The Loan Summary API now also returns:

```json
{
  "debug": {
    "financial_pipeline": {
      "financial_source": {},
      "document_types": [],
      "metrics_rupees": {},
      "ratios_pre_context": {},
      "financials_crore": {},
      "ratios_final": {}
    }
  }
}
```

This allows you to copy the Loan Summary API JSON and send the `debug.financial_pipeline` object for diagnosis.

## Safety fix included

If an Annual Report exists, the code no longer silently falls back to the legacy whole-document financial regex. If structured extraction cannot be trusted, the financial card returns unavailable values rather than impossible figures.

Structured financials also run sanity checks such as PAT not exceeding revenue and PAT margin staying within a plausible range. Failed validation is printed under `validation_errors`.

## Annual-report section fix

The statement selector no longer blindly takes the last `BALANCE SHEET` / `PROFIT AND LOSS` heading. It scores candidate headings using expected statement rows, reducing the chance of selecting a table-of-contents or notes occurrence.
