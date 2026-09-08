# Borrower Information field layout fix v12.1

## Problem
Long values in Step 6 Corporate Profile were rendered one character per line because the row reserved four grid columns (label, value, source, status). On some viewport/sidebar widths the value column collapsed to only a few pixels, while `overflow-wrap:anywhere` allowed breaking at every character.

## Fix
- `FieldRow` now uses three visual columns: label | value+source | status.
- Source provenance is stacked below the field value instead of consuming a separate fixed-width column.
- Removed character-level wrapping for borrower field values.
- Added responsive minimum widths to the Step 6 top grid.
- Added mobile layout that stacks label/value cleanly rather than squeezing text.

No backend/API logic was changed by this patch.
