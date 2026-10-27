# Original-neighbor contact support comparison

The 21 previously detected candidate-to-original contacts were compared on
the **unchanged neighboring surface's face IDs**. For each relation, supporting
faces were deduplicated before area and centroid calculation. Baseline and
candidate detections had complete triangle-pair coverage; the archived Atlas
and prior loft-index hashes were verified.

## Findings

- 4/21 relations retain exactly the same supporting face set.
- Across the 21 directional relations, 21 face memberships are gained and
  206 are lost. Counts are per relation, not unique faces across the Atlas.
- Maximum displacement of the area-weighted support-facet centroid is
  **1.847353 mm**.

| Candidate → neighbor | Original support faces | Candidate support faces | Support centroid shift (mm) |
|---|---:|---:|---:|
| FJ1692M:e0 → FJ1682M | 43 | 10 | 1.847353 |
| FJ1692:e0 → FJ1682 | 43 | 11 | 1.660192 |
| FJ1692M:e0 → FJ1718M | 28 | 14 | 1.223074 |
| FJ1654M:e0 → FJ1692M | 37 | 7 | 1.217979 |
| FJ1654:e0 → FJ1676 | 29 | 6 | 1.044864 |

These metrics describe the whole original facets touched by intersecting
triangles. They are **not intersection area, overlap volume, opening area or
anatomical junction displacement**. Face size and distribution affect the
centroid. No acceptance threshold has been set from these measurements.

The baseline uses complete original parts whereas the candidates are open
interior strips. Therefore missing end geometry can contribute to lost support;
the results cannot isolate deformation from endpoint omission. Full-end/junction
preservation must be implemented before this can become a like-for-like
junction-preservation test. Identical support sets alone would not prove opening
shape preservation either.

## Implementation and verification

`compare_contact_footprints` reports before/after/retained/gained/lost face IDs,
support areas, weighted centroids and face-set Jaccard similarity. Empty sets
produce no fabricated centroid displacement; repeated contact pairs do not
inflate area. Unknown IDs and degenerate support faces are rejected.

**8 tests passed**, including support weighting, duplicate IDs, empty sets,
invalid indices and the prior mesh-pair tests. Original geometry and the live
scene remain unchanged.

```text
python -m pytest tests/test_contact_footprint.py tests/test_mesh_pair_contact.py -q
python scripts/inspect_cerebral_contact_footprints.py
```

- [All relation measurements and supporting face IDs](evidence/cerebral-contact-footprints.json)
- [Regression results](evidence/contact-footprint-tests.xml)
