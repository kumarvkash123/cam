# V11 Sidebar + Borrower State Fix

## Borrower page
- Existing borrower search is local `searchQuery` state.
- Existing borrower selection is local `selectedBorrower` state.
- Create-new company name is local `newBorrower.companyName` state.
- Typing in the Create New Borrower form no longer changes the search box.
- Searching/selecting an existing borrower no longer fills the Create New Borrower form.
- Existing borrower selection now shows an explicit selected panel and Continue action.
- `startCam(companyOverride)` accepts the selected/new company explicitly, then commits the final borrower to Redux only when CAM creation begins.

## Sidebar
- Kept one CAM navigation sidebar only.
- Removed duplicate active-state mappings where multiple menu buttons pointed to the same step.
- Exactly one menu entry is active for each CAM step.
- Reworked collapsed/expanded sizing and main content offsets.
- Toggle now belongs to the sidebar brand row instead of floating as a separate visual layer.
- Collapsed sidebar hides the logo so the toggle and brand cannot overlap.
- Added sidebar overflow scrolling and responsive rules.
- Added titles/ARIA labels for collapsed navigation usability.
- Corrected responsive CSS that previously hid labels even when the sidebar was expanded.
