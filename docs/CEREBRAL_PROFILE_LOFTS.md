# Open noncircular cerebral surface candidates

The profile loft generator resamples each closed measured contour at 64 equal
perimeter intervals, orients it against its declared normal and chooses the
cyclic shift minimizing squared distance to the preceding ring. Adjacent rings
are triangulated. Unknown, missing/nonconsecutive or degenerate profiles are
rejected. Inputs remain unchanged.

This creates a piecewise-linear lateral candidate, not an approved smooth
vessel. It deliberately has two open boundaries at the first and last measured
interior sections. Source endpoints, caps and junctions are not reconstructed.
Perimeter resampling does not preserve every original polygon corner.

All eight fixed-cohort paths generated candidates, totaling 33,600 vertices
and 66,176 triangles. Each has consistent winding and 128 boundary edges.
Original triangle and profile hashes were checked before generation.

## Measured original-surface distances

| Edge | Largest face-centroid sample distance (mm) | Corresponding station pair |
|---|---:|---|
| FJ1654:e0 | 0.095393 | 24–25 |
| FJ1654M:e0 | 0.106777 | 22–23 |
| FJ1660:e0 | 0.047148 | 5–6 |
| FJ1660M:e0 | 0.036563 | 22–23 |
| FJ1692:e0 | 0.058831 | 56–57 |
| FJ1692M:e0 | 0.049687 | 2–3 |
| FJ1694:e0 | 1.081462 | 43–44 |
| FJ1694M:e0 | 0.279930 | 86–87 |

Resampled vertices remain close to the original triangles (largest residual
3.456e-7 mm), but interpolating between contours can create substantially larger
errors. Each triangle centroid was checked; this is one-way finite sampling,
not a continuous or bidirectional surface-error bound. Worst sample coordinates
and station pairs are retained for diagnosis. No acceptance threshold was
introduced after seeing these results.

The right MCA `FJ1694:e0` 43–44 transition needs investigation before promotion:
good contour vertices alone do not validate the intervening surface. Candidates
remain outside the live Atlas editor. Self-intersection, neighboring vessels,
smoothness, caps, junctions and anatomical validity remain NOT RUN.

## Verification and artifacts

**10 tests passed** for original profile extraction and loft generation,
including nonround rectangular area/shape, unmodified input, reversed contour
orientation and cyclic starting positions, open topology and rejection of
missing/unknown/invalid profiles.

```text
python -m pytest tests/test_profile_loft.py tests/test_source_sections.py -q
python scripts/inspect_cerebral_profile_lofts.py
```

- [Candidate paths, hashes and measurements](evidence/cerebral-profile-lofts.json)
- [Regression tests](evidence/profile-loft-tests.xml)

PLY candidates are stored under content-addressed
`exports/cerebral-profile-lofts/` directories. Original source files are unchanged.
