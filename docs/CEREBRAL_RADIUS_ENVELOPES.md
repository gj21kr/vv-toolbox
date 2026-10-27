# Cerebral radius-envelope inspection

## Result

The frozen eight-edge cohort has **0 PASS / 8 FAIL / 0 UNKNOWN** for both
original and smoothed linear-radius ball envelopes. This differs from the
centerline-only result, which passed all 533 intervals in each group.
All 533 initial interval midpoints in each group have stored interpolated
radii greater than the nearest source-triangle distance by more than 1e-6 mm.
No tested midpoint center is outside the source solid.

| Edge | Source maximum excess (mm) | Smoothed maximum excess (mm) |
|---|---:|---:|
| FJ1654:e0 | 0.44 | 0.42 |
| FJ1654M:e0 | 0.45 | 0.44 |
| FJ1660:e0 | 0.35 | 0.39 |
| FJ1660M:e0 | 0.37 | 0.38 |
| FJ1692:e0 | 0.46 | 0.52 |
| FJ1692M:e0 | 0.46 | 0.46 |
| FJ1694:e0 | 0.38 | 0.47 |
| FJ1694M:e0 | 0.37 | 0.45 |

Values are rounded for display; raw positions, interpolation fractions, radii
and excesses are retained in the evidence. These are witness measurements, not
global maximum deviations or measurements of reconstructed wall penetration.
The source/result revisions, original file and triangle hashes are checked
against the existing fixed-cohort records before inspection.

## Definition and limits

The inspected envelope is the union of balls whose centers and radii interpolate
linearly along each centerline segment. For an adaptive interval, the distance
from its midpoint to the nearest triangle must exceed the interval half-length
plus the larger endpoint radius plus tolerance. With an interior midpoint and a
valid closed solid, this sufficient bound covers every ball in that interval.
Otherwise the interval is subdivided. An interior midpoint radius exceeding the
nearest-boundary distance plus tolerance is a numerical envelope FAIL witness.
Boundary ambiguity or resource exhaustion remains UNKNOWN.

The union of balls conservatively contains circular normal sections but may
extend beyond tube end caps. **Envelope FAIL is not tube-wall FAIL.**
The checker does not establish radius accuracy, source self-intersection,
anatomical identity, reconstructed wall quality or inter-vessel separation.
It is a floating-point inspection under the same closed-solid assumptions as
the centerline inspection.

The stored radii and original surfaces remain unchanged. The result does not
justify shrinking radii to force containment: actual normal sections and the
intended lumen shape must determine any separate synthetic radius correction.
This inspection is currently offline and does not alter the workbench's
centerline-only PASS display.

## Verification and reproduction

Docker regression: **25 passed**, including centerline-in/radius-out cases,
variable-radius exits missed by the initial midpoint, positive clearance,
tangent ambiguity, budget exhaustion, invalid radii and prior workbench checks.

```text
python -m pytest tests/test_radius_envelope_containment.py tests/test_centerline_containment.py tests/test_workbench_containment.py -q
python scripts/inspect_cerebral_radius_envelopes.py
```

- [Cohort evidence](evidence/cerebral-radius-envelopes.json)
- [Regression evidence](evidence/radius-envelope-containment-tests.xml)
- [Prior centerline-only comparison](WORKBENCH_CEREBRAL_SMOOTHING_CHECK.md)

User Atlas snapshot SHA256 remained
`082a9178daee4d52c79aaa709cba91fbdc56cfb5767fef4801fd4b9bb22d1964`.
