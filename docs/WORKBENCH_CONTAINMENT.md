# Saved-case source-surface inspection

The `/case-labels` workbench provides **Check against original surface** for
the selected edge. It is an explicit read-only inspection; it does not prevent
editing or downloading, mutate the case, or approve an anatomical model.

Before comparison the service requires the recorded native BodyParts3D frame
(ID, LPS axes, mm units and unchanged origin), the pinned archive hash among
the selected edge's source references, and an explicit `source_part_id`.
It never derives this mapping from an edge name. Missing bindings, unavailable
registered files or a missing surface return UNKNOWN. The recorded binding is
a declaration, not independent proof of anatomical identity.

The checker covers full polyline intervals using the numerical interior-ball
criterion in [the cerebral smoothing inspection](WORKBENCH_CEREBRAL_SMOOTHING_CHECK.md).
Interactive limits are 10,000 input points and 20,000 subdivision cells.
Exhausted subdivision budgets remain UNKNOWN. Outside witnesses return FAIL.
Closed-solid and floating-point assumptions remain applicable; self-intersection,
radius accuracy, other-vessel collisions and anatomy are not validated here.
Exact-index surface copies preserve triangle coordinates.

Responses carry the exact case revision, edge ID, original part, archive hash,
surface triangle hash and detailed interval results. The page clears its result
when selection or case state changes, including smoothing and undo/redo.
Inspection results are displayed separately from the editable case.

## Verification

- Docker regression: **29 passed**, covering read-only behavior, source binding,
  different coordinate origin, missing surfaces/files, actual outside witnesses,
  smoothing and preview regressions.
- Browser: unbound synthetic fixture UNKNOWN; original and smoothed `FJ1692:e0`
  PASS, with different case revisions. Modification, undo and changed selection
  invalidate the displayed result. No page errors or horizontal overflow at
  390 px. This does not claim all Atlas parts pass.
- User Atlas edit snapshot remained
  `082a9178daee4d52c79aaa709cba91fbdc56cfb5767fef4801fd4b9bb22d1964`.
- Browser plugin not available; used Playwright over the existing local CDP
  browser, in a separate test tab.

Evidence: [regression XML](evidence/workbench-containment-tests.xml),
[browser results and measurements](evidence/workbench-containment-browser.json).

Reproduce:

```text
python -m pytest tests/test_workbench_containment.py tests/test_label_workbench.py tests/test_centerline_containment.py tests/test_case_preview_ui.py -q
node scripts/verify_workbench_containment.cjs
```
