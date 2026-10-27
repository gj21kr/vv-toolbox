# Noncircular original cerebral profiles

`extract_source_sections` retains the complete unique closed source contour
enclosing each non-endpoint centerline station. Profiles include the local
plane origin and orthonormal basis, UV and original-frame XYZ coordinates,
area, area-equivalent radius, area centroid and center-to-boundary distance.
The contour is not replaced by a circle and its centroid is not automatically
used to move the centerline. Multiple enclosing contours and degenerate planes
remain UNKNOWN.

The original eight-edge cohort produced **525 MEASURED / 0 UNKNOWN** profiles.
All **23,535 saved contour vertices** were compared with their original triangle
surfaces; the largest nearest-surface residual was **2.511143e-13 mm**.
This numerical vertex agreement is not a proof of continuous inter-profile
surface agreement, self-intersection freedom or anatomical accuracy.

The source snapshot revision, archive and triangle hashes are verified against
the earlier radius-section inspection. Each profile artifact is stored in an
immutable-content-addressed directory under `exports/cerebral-source-sections/`;
the Git-tracked evidence lists its path, SHA256, counts and measured residual.
Existing different content at the same destination is rejected.

## Why retain contours

The current source extractor uses `distance_transform_edt(mask) * pitch`,
which measures distances to background voxel centers. It subsequently smooths
the centerline while interpolating the stored radius. Those values are not
new nearest-triangle distances at the moved centers. This is an implementation
observation, not a quantitative attribution of all observed radius errors.

The [normal-plane inspection](CEREBRAL_RADIUS_SECTIONS.md) also shows that
area-equivalent radius alone cannot represent every asymmetric or off-center
section. Retaining the original contour makes it possible to construct a
separate noncircular synthetic surface and compare it with the original.
No arbitrary scalar radius correction has been applied.

## Scope still open

These are section measurements, not an accepted vessel reconstruction.
Endpoint/cap sections, correspondence between consecutive contours, a connected
surface, junction preservation, self/inter-vessel collision checks, editor
integration and mask export remain unimplemented for this profile representation.
Existing source surfaces, centerlines and radii remain unchanged.

## Tests and reproduction

**11 tests passed**: rectangular shape/area/centroid preservation, original
immutability, unresolved outside axes and zero tangents, ambiguous nested
contours, rigid coordinate transforms and existing circular-profile checks.

```text
python -m pytest tests/test_source_sections.py tests/test_radius_sections.py -q
python scripts/extract_cerebral_source_sections.py
```

- [Source profile artifact index](evidence/cerebral-source-section-profiles.json)
- [Regression results](evidence/source-sections-tests.xml)
