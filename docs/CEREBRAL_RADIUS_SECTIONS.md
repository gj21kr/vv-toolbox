# Cerebral normal-plane radius comparison

The same frozen eight-edge cohort was checked at every non-endpoint station.
The local normal plane uses the chord between the previous and next centerline
points. Each stored circular profile is sampled at 64 equally spaced angles.
Samples are compared with the unchanged original surface using inside queries
and nearest-triangle distance; points within 1e-6 mm of the surface are ambiguous.

| Group | Sections | Sections with outside witnesses | Outside samples / total | Ambiguous samples |
|---|---:|---:|---:|---:|
| Original centerlines | 525 | 525 | 26,917 / 33,600 | 0 |
| Smoothed centerlines | 525 | 525 | 28,887 / 33,600 | 0 |

All eight paths in both groups therefore have **FAIL for sampled circular
profiles**. Each FAIL contains explicit coordinates, station and angular sample
indices, local plane normal, radius and distance from the source surface.
This resolves the previous ambiguity that the ball-envelope failure might
arise only from spherical end extensions: these are non-endpoint normal-plane
circle samples.

This is not a measurement of a rendered or reconstructed tube mesh, continuous
wall penetration volume, anatomical accuracy or clinical validity. Source
self-intersection is still NOT RUN. Centerline-only containment remains a
separate PASS result.

## Radius and cross-sectional area

The previously measured unique enclosing original contours were joined by
station index after checking source file, case revision, result revision,
archive and ordered triangle hashes. The associated measurement report hash
is recorded. Stored radius divided by contour area-equivalent radius ranges:

- Original: **0.715928–1.268030**.
- Smoothed: **0.856311–1.278269**.

These ranges are descriptive, not a radius acceptance tolerance. A radius
smaller than the area-equivalent radius can still put a circular profile outside
an asymmetric contour or a contour whose center differs from the centerline.
Consequently, scaling every radius by one factor or replacing it with the
area-equivalent radius does not establish shape agreement.

The source radii and surfaces are unchanged. A synthetic correction needs to
account for the section contour, center position, intended circular versus
noncircular representation and preservation of neighboring junctions. Smoothing
alone does not resolve the observed discrepancy.

## Verification

**24 tests passed** in Docker, covering inside and outside profiles, boundary
ambiguity, actual open surfaces, zero chord tangents, invalid radii, rigid
coordinate transformations and the prior whole-interval/envelope checks.
The actual cohort retained all 525 sections per group; no failures were omitted.

```text
python -m pytest tests/test_radius_sections.py tests/test_radius_envelope_containment.py tests/test_centerline_containment.py -q
python scripts/inspect_cerebral_radius_envelopes.py --normal-sections
```

- [Measurements and outside witnesses](evidence/cerebral-radius-sections.json)
- [Regression tests](evidence/radius-sections-tests.xml)
- [Previous envelope inspection](CEREBRAL_RADIUS_ENVELOPES.md)
