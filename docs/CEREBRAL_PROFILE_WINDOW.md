# Physical-window section frames

## Change

`extract_source_sections` now accepts an explicit positive
`tangent_half_window_mm`. For each unchanged station, the tangent is the chord
between interpolated positions at arclength minus/plus that window, clipped to
the path ends. This reduces sensitivity to short-step direction changes.
The default previous/next-station mode remains available for reproducibility.
No centerline point, radius or source-surface vertex is changed by this option.

The comparison used the existing fixed smoothed paths and a **2 mm half-window
on all eight paths**, selected before running this comparison. All 525 interior
profiles were measured. No section was omitted and no per-edge window was tuned.
The loft method remains 64 perimeter samples and cyclic correspondence.

## Complete serialized-surface self-contact result

All **8/8 exported PLY candidates have NO_CONTACT_DETECTED** under the existing
1e-8 mm finite-precision checker, including shared-topology overlap checks.
All-pair broad-phase coverage completed on each candidate; none exhausted its
2,000,000-pair budget.

| Edge | Prior contact pairs | Window candidate contact pairs | Window face-centroid maximum distance to source (mm) |
|---|---:|---:|---:|
| FJ1654:e0 | 91 | 0 | 0.074413 |
| FJ1654M:e0 | 98 | 0 | 0.076823 |
| FJ1660:e0 | 74 | 0 | 0.028999 |
| FJ1660M:e0 | 111 | 0 | 0.027321 |
| FJ1692:e0 | 0 | 0 | 0.036028 |
| FJ1692M:e0 | 28 | 0 | 0.033277 |
| FJ1694:e0 | 174 | 0 | 0.065007 |
| FJ1694M:e0 | 116 | 0 | 0.056165 |

Source-distance samples improve on seven paths; FJ1654:e0 increases from
0.070017 to 0.074413 mm. The contact improvement is not a claim that every
geometric metric improves or that 0.1 mm is an accepted threshold.

This supports local section-frame variation as a contributor to the previous
strip overlaps. It does not establish exact-arithmetic intersection freedom,
continuous/bidirectional surface error, cap correctness, inter-vessel clearance,
junction preservation or anatomical validity. The candidates still end at open
interior section boundaries and remain outside the live Atlas model.

## Verification and artifacts

**15 tests passed** covering profile extraction and lofting, including physical
window behavior with irregular station spacing, unchanged section origins,
invalid window rejection and earlier contour/correspondence cases.
The actual 8-path geometry run and full serialized-surface contact run provide
the cohort evidence above. Earlier source/local-frame candidates are retained.

```text
python -m pytest tests/test_source_sections.py tests/test_profile_loft.py -q
python scripts/extract_cerebral_source_sections.py --smoothed --tangent-window-mm 2
python scripts/inspect_cerebral_profile_lofts.py --smoothed --tangent-window-mm 2
python scripts/inspect_cerebral_loft_contacts.py --tangent-window-mm 2
```

- [Profile artifact index](evidence/cerebral-smoothed-section-profiles-window2mm.json)
- [Loft geometry and sampled distances](evidence/cerebral-smoothed-profile-lofts-window2mm.json)
- [Complete contact coverage](evidence/cerebral-loft-self-contact-window2mm.json)
- [Regression results](evidence/profile-window-tests.xml)
