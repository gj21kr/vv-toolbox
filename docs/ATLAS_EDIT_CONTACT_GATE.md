# Atlas edit self-contact gate

Non-default atlas edits now run the self-contact screen before scene mutation.
Reload checks regenerated surfaces before replacing the current graph or handles.
Save checks each modified surface before writing the parameter snapshot.
Restoring the original atlas remains possible without accepting its inherited
geometry as a validated edited model.

The gate rejects detected contacts and incomplete/unknown inspection results.
It records the detailed result under `edit_checks.self_contact_screen` and the
scoped status under `edit_checks.self_intersection`. Save/reload failures use
HTTP 422 with `atlas_edit_checks_failed`, consistent with modification failure.
The existing default v1 deformation and saved generator identity are unchanged.

## Verification

Container command:

```text
python -m pytest tests/test_atlas_edit_checks.py tests/test_atlas_edit_session.py tests/test_atlas_workspace.py -q
```

**PASS: 37 tests**, including:

- Crossing triangles rejected; separated triangles accepted.
- Degenerate geometry produces UNKNOWN and is rejected.
- Rejected modification/reload leaves graph, generation and edited-surface
  mappings unchanged.
- Failed save preserves existing snapshot bytes.
- Successful edits export the measured self-contact status.
- Original restoration and existing save/reload behavior remain covered.

The generated crossing output used for workspace failure injection is synthetic.
These unit tests are complemented by the browser checks below.

## Live browser verification

**PASS** using Playwright over the existing CDP browser at
`http://127.0.0.1:8093/`, title `VV Toolbox`, captured viewport 1500×1112.
The Browser plugin was unavailable. The browser reported software WebGL.

- FJ1692 radius 2, tortuosity 1, torsion 180 produced 36 contact pairs and
  HTTP 422. The error appeared in the UI.
- Generation, graph, modified surfaces and isolated snapshot bytes remained
  unchanged after rejection.
- Radius-only 1.3 passed the self-contact screen and completed
  save → reset → reload with identical regenerated surface data.
- The screen displayed self-intersection PASS while surrounding collision and
  junction smoothness remained NOT RUN.
- The test ended at unmodified geometry. No page JavaScript errors occurred.
- The normal demo was restarted with its default storage path. The original
  user snapshot hash remained
  `082a9178daee4d52c79aaa709cba91fbdc56cfb5767fef4801fd4b9bb22d1964`.

An additional UI defect was found: save availability cached while centerlines
were loading was not refreshed when readiness changed within the same
generation. The refresh key now includes source, generation and centerline
readiness. A controlled browser readiness transition verifies that Save becomes
enabled without changing server geometry or generation.

Tracked evidence: `evidence/atlas-contact-gate-browser.json` and
`evidence/atlas-save-readiness-browser.json`.
Screenshots: `exports/atlas-contact-gate-verification/rejected-edit.png` and
`exports/atlas-contact-gate-verification/accepted-edit.png`.

Cold-reload attempts exceeded the 60-second control-readiness wait in this
software-rendering environment; the successful interaction test used an
already-loaded tab. Cold-load performance remains unverified. An initial test
also incorrectly expected HTTP 200 instead of the valid 202 modification
response; the test now accepts both success statuses.
Live browser rejection of a failing saved snapshot remains NOT RUN; that
rollback path is covered by unit tests.

## Scope

PASS here means no self-contact detected within the finite-precision screening
scope. It does not establish surrounding-vessel clearance, surface/radius
agreement, junction smoothness, volume containment, or anatomical validity.
Experimental v2/v3 flow and radius-correction candidates remain outside the
default editing path. Their failures are retained in separate inspection
evidence and are not turned into accepted exports by this change.
