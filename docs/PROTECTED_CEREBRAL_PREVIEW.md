# Protected cerebral source/candidate preview

The Atlas page's synthetic-candidate selector now includes:

- **뇌혈관 8개 · 원본 비교**: the eight original surfaces.
- **뇌혈관 8개 · 끝단 보존 보정 후보**: the eight protected fitted surfaces.

The comparison button switches between the same eight parts, and **Atlas로
돌아가기** restores the Atlas workspace. Both comparison states are read-only.
The source files and saved Atlas edits are not replaced. Only these eight
surfaces are displayed; this is not a full arterial-network replacement.
Centerline mode is hidden for this surface-only comparison because updated
centerline/radius consistency has not been established.

## Evidence-bound loading

The loader verifies original archive identity, candidate/report hashes,
complete affected-pair coverage, preserved contact face-pair sets and complete
candidate self-contact screening. It reloads each serialized candidate and
checks unchanged face topology and exact protected coordinates.
Missing, altered or incomplete evidence rejects loading before scene selection.
Candidate paths must resolve within registered local exports.

The UI separately displays the source/candidate identity, read-only scope and
remaining centerline/radius, volume-containment and anatomical uncertainties.
The renderer description supports this candidate type explicitly so camera
fitting completes after selection.

## Verification

Loader and candidate regressions: **13 passed**, including altered artifacts,
stale report hash, missing pair coverage, source/candidate separation and the
renderer-description regression.

Browser reproduction:

```text
node scripts/verify_protected_preview.cjs
```

The script checks both comparison directions, successful source-switch HTTP
responses, rejection of edits in candidate mode, surface-only controls, narrow
viewport layout, Atlas return and preservation of the saved Atlas snapshot.
The final browser run passed all these checks with zero page errors, and both
source and candidate captures were visually inspected. The final script
preselects the read-only candidate through the API before opening its test tab
to avoid loading the full Atlas into that tab first. Earlier runs also exercised
the Atlas-to-candidate button. The observed software WebGL renderer made full
Atlas entry/return slow; this is not a hardware-rendering performance result.
Browser plugin is unavailable, so it uses Playwright through the existing
local CDP browser in a separate test tab.

Initial checks exposed a missing renderer-description field that interrupted
camera fitting; this was corrected and added to the regression test. The
browser response assertion accepts successful 2xx responses, including the
source-switch endpoint's normal 202 response.

- [Regression results](evidence/protected-preview-tests.xml)
- [Browser verification](evidence/protected-preview-browser.json)
- Local visual captures: `exports/protected-preview/candidate.png` and
  `exports/protected-preview/reference.png`.

This preview is not acceptance of anatomical boundaries, complete access
routes or clinically validated geometry.
