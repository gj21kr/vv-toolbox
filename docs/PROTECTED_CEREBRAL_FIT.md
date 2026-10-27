# Complete source-topology cerebral candidates

## Method

`fit_protected_surface` creates a separate copy of the original mesh, preserving
the exact face indices. Movable vertices project toward the previously inspected
noncircular window-profile target. A three-edge-ring smoothstep transition
weights displacement away from protected vertices. The declared displacement
bound is 0.3 mm; excess motion, reversed faces or degenerate faces are rejected.

Exact duplicate-coordinate vertices move together; protecting one protects all
its aliases. The original mesh and its index representation remain unchanged.

For each of eight original parts, every other original arterial part was checked
for surface contact. All vertices of contacting original faces were protected;
incomplete contact coverage aborts the run. Vertices beyond the first/last
interior section planes are also protected. These conservative half-space masks
can preserve additional interior areas on curved vessels. They are geometric
protection rules, not independently annotated anatomical endpoint labels.

Unlike the previous open lofts, the resulting candidates retain all original
end geometry and all detected original contact triangles. No new cap is created.
The frozen targets are guidance surfaces, not replacements of complete parts.

## Actual cohort

| Edge | Moved vertices | Maximum movement (mm) | Protected original contact relations |
|---|---:|---:|---:|
| FJ1654:e0 | 82 | 0.032404 | 7 |
| FJ1654M:e0 | 86 | 0.045811 | 7 |
| FJ1660:e0 | 216 | 0.025913 | 3 |
| FJ1660M:e0 | 216 | 0.036009 | 3 |
| FJ1692:e0 | 205 | 0.032948 | 6 |
| FJ1692M:e0 | 203 | 0.026081 | 6 |
| FJ1694:e0 | 1,855 | 0.072530 | 5 |
| FJ1694M:e0 | 1,843 | 0.062930 | 5 |

All eight serialized PLY candidates preserve protected coordinates exactly.
After inspection-only exact-coordinate index normalization, all eight are
watertight and consistently oriented, and the full self-contact checker reports
NO_CONTACT_DETECTED. Source faces are unchanged. Original files and live Atlas
geometry are not modified.

The 42 protected original contact relations exceed the earlier open-candidate
list because this protection pass screens complete original parts, including
their ends. It does not infer that all source intersections are valid anatomical
junctions. Preserving existing contact faces also does not exclude new contacts
from other moved faces; a new complete surroundings audit is still required.

## Validation limits

These are CANDIDATE results, not accepted anatomy or completed editing support.
New neighboring contacts, simultaneous replacement of multiple parts, smoothness
and radius/centerline consistency need follow-up. Closed index topology does
not independently prove anatomical lumen connectivity.

**9 tests passed** for protected fitting and lofting, including original
immutability, exact protected positions, duplicate-coordinate aliases, unchanged
face topology and rejection of excess displacement.

```text
python -m pytest tests/test_protected_surface_fit.py tests/test_profile_loft.py -q
python scripts/inspect_protected_cerebral_fit.py
```

- [Candidate artifacts, protection masks and full self-contact evidence](evidence/protected-cerebral-fit.json)
- [Regression tests](evidence/protected-surface-fit-tests.xml)
