# Financial Note Column Fix V31

This patch fixes the remaining Loan Summary financial extraction issue identified by `[CAM-FIN-DEBUG]`.

## Root cause
Annual-report statement rows can be extracted across multiple lines, for example:

```
Revenue from Operations
28
16,329.01
11,639.93
```

`28` is the Note No. The previous parser returned too early after seeing two numeric tokens, so Note Nos. such as 28, 34, 3, 7, 8, 9, 14 and 15 could be used as financial amounts.

## Fix
- Gather the complete logical row before choosing numeric values.
- When a leading small integer is present, treat it as a Note No. and use the last two numbers as current/previous-year amounts.
- Keep `[CAM-FIN-DEBUG]` tracing and add a `critical_rows` snapshot for revenue, finance cost, depreciation, inventory and borrowings.
- Frontend `cr()` and `ratio()` now preserve null as `Not available`; null DSCR, debt and debt/equity no longer render as `0.00`.

## Expected result
After reloading Loan Summary, debug values such as `revenue_from_operations_current`, `finance_cost_current`, `depreciation_amortisation_current`, `inventories_current`, `current_borrowings_current`, and `non_current_borrowings_current` should be actual statement values rather than Note Nos.
