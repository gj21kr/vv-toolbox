# Atlas shared deformation field check

The experimental `field_version='v2'` evaluates source surface vertices and
centerline coordinates with the same function. Spatial protection is applied
once, after interpolation; duplicate protection constraints are removed.
The default remains v1, including existing saved-session replay behavior.

## Verification

- Docker: `python -m pytest tests/test_atlas_modification.py tests/test_atlas_edit_session.py -q`
  — **PASS**, 48 tests.
- Identical source coordinates embedded as unused mesh probes and centerline
  points produce exactly identical v2 coordinates.
- Repeated identical protection regions do not change v2 output.
- Default and explicit v1 outputs remain identical in the regression fixture.

Actual atlas inspection:

```text
python scripts/inspect_atlas_edit_surroundings.py --protect-contacts --transition-width-mm 8 --anchor-blend product --field-version v2
```

For FJ1692, radius scale 1.3, tortuosity 0.3, torsion 35 degrees:

| Observation | Result |
|---|---|
| Other native arterial parts checked | 517 |
| New / removed contacting parts | 0 / 0 |
| Original contacting surface vertices | Exactly preserved |
| Maximum surface / centerline movement | 4.319 / 4.039 mm |
| New boundary face pairs exceeding 90 degrees | 0 |
| Self-contact | **FAIL: 9 triangle pairs detected** |
| Volume containment | NOT RUN |
| Anatomical validity | UNKNOWN |

Evidence: `evidence/atlas-mca-protected-edit-surroundings-width8-product-v2.json`.
The inspection did not change the live workspace.

## Decision

Do not promote v2 to the app default. Sharing the field fixes inconsistent
coordinate transformation but does not establish a valid surface. Nearest-eight
sample selection can still introduce discontinuities, and protection gradients
can fold the mesh. Reported radius scaling is not yet a measured cross-sectional
radius; radius-only centerline drift also needs characterization.

The next correction must address interpolation continuity and local deformation
gradients, with the same requested parameters and contact checks retained.

## Fixed-support interpolation experiment

`field_version='v3'` replaces nearest-eight selection with normalized compact
weights `(1-q)^4 (4q+1)` for `q < 1`. The support radius is frozen from source
geometry: the larger of three times the median source centerline radius and
twice the largest source-vertex distance to its nearest centerline sample.
Unsupported queries are rejected. This support rule provides coverage for
source vertices; it does not establish branch-specific correspondence.

The weights approach zero smoothly at the support boundary. A test moves a
query across a sample's support boundary while another sample retains support;
the output difference converges to zero with decreasing step size. Shared
coordinate transformation and duplicate-constraint tests also cover v3.
The targeted Docker test run passed **50 tests**.

Actual FJ1692 inspection uses the same parameters and protection regions as v2:

| Observation | v3 |
|---|---|
| Other native arterial parts checked | 517 |
| New / removed contacting parts | 0 / 0 |
| Original contacting vertices | Exactly preserved |
| Maximum surface / centerline movement | 4.313 / 3.910 mm |
| Self-contact | **FAIL: the same 9 triangle pairs as v2** |
| New boundary face pairs exceeding 90 degrees | 0 |

Evidence: `evidence/atlas-mca-protected-edit-surroundings-width8-product-v3.json`.
The failed result shows that removing nearest-eight membership discontinuities
is insufficient for this case. Protection gradients and individual deformation
components need isolation; changing requested parameters to obtain a pass is
not part of this experiment. v3 remains opt-in and is not enabled in the demo.

## Component isolation

`scripts/inspect_atlas_edit_components.py` checks all 16 combinations of
contact protection on/off and radius/bend/twist enabled/disabled. Enabled values
remain 1.3, 0.3, and 35 degrees. Endpoint collars remain active in every case.
The script checks the exact export and source surface against the v3 inspection
before running and stores an implementation hash.

| Enabled components | Contact protection off: self-contact pairs | On: self-contact pairs |
|---|---:|---:|
| Identity | 0 | 0 |
| Rotation | 0 | 0 |
| Bend | 0 | 0 |
| Bend + rotation | 0 | **10** |
| Radius | 0 | 0 |
| Radius + rotation | 0 | 0 |
| Radius + bend | 0 | 0 |
| Radius + bend + rotation | 0 | **9** |

This isolates failure to the combined bend/rotation under the tested contact
constraints; radius expansion is not necessary for failure. It does not prove
which term of the spatial gradient causes each intersecting pair. Disabling
contact constraints is not an acceptable correction because it permits movement
of attachment geometry.

Radius-only editing moves the centerline by **0.022172147988317552 mm** with and
without contact protection. This confirms that interpolated radial vectors do
not fix the original centerline exactly. The shared evaluator guarantees
coordinate correspondence, but not radius-only centerline preservation.

Evidence: `evidence/atlas-mca-edit-component-isolation.json`. All 16 cases
completed. Surrounding vessel collision and containment were not repeated in
this component-isolation experiment; zero self-contact is not overall PASS.

Next implementation work should replace direct displacement blending at fixed
attachment regions with a deformation that controls local folding, and correct
the radial field's centerline drift. Preserve the combined requested parameters
as the regression case rather than removing either component.

## Radius-only centerline preservation

An opt-in `radial_mode='polyline'` for v3 computes the radial vector from the
closest point on the original centerline segments. Separate paths are not
joined by invented segments. Compact interpolation still determines the scale
and bend displacement. Default tangent interpolation and saved sessions retain
their previous behavior.

The curved synthetic fixture preserves centerline coordinates exactly under
radius-only editing while moving surface vertices and increasing the reported
radii. A separate disconnected-path test verifies that the projection does not
use an artificial segment across the gap. The targeted Docker run passed
**52 tests**.

The full 16-case MCA isolation was repeated with this mode:
`python scripts/inspect_atlas_edit_components.py --radial-mode polyline`.
Both radius-only cases now have **0.0 mm centerline movement**, versus
0.022172147988317552 mm previously. For every tested bend/rotation combination,
adding radius scaling no longer changes the returned centerline.
Self-contact counts remain unchanged: 10 pairs for protected bend+rotation and
9 for protected radius+bend+rotation. The radius correction therefore resolves
the measured drift, not the attachment-region folding.

Evidence: `evidence/atlas-mca-edit-component-isolation-polyline.json`.
Nearest-segment projection can be ambiguous between nearby branches and is not
globally differentiable at all segment changes. Cross-sectional accuracy and
volume containment remain unverified. This candidate is not enabled in the app.

## Integrated field candidate

The optional `integration_steps=32` uses RK4 to integrate the stationary field
over unit time. It requires v3/polyline. Radial scales become logarithmic rates;
bend/twist displacement is explicitly interpreted as velocity. Consequently
this is a different deformation interpretation, not evidence of exact agreement
with the previous requested angular displacement.

An initial run rejected a query outside compact support. The corrected support
is fixed before integration using the larger of the original support and
`2 exp(max_rate) (max_source_distance + max_shift)`. This conservative spatial
envelope follows the bound `d' <= max_shift + max_rate*d` for distance to the
original polyline. It is not a guarantee on numerical RK4 error. The wider
support also changes interpolation, so any difference cannot be attributed to
integration alone.

The same MCA combined case completed:

- Original contact vertices remain exactly fixed.
- No new or removed contacting vessel IDs among 517 other arterial parts.
- Surface / centerline maximum movement: 3.878 / 3.480 mm.
- **Self-contact FAIL: 6 triangle pairs remain**, compared with 9 in direct v3.
- No new fixed/moving boundary pairs above 90 degrees.
- Containment and anatomical validity remain unverified.

Evidence:
`evidence/atlas-mca-protected-edit-surroundings-width8-product-v3-polyline-flow32.json`.
Analytic constant-rate expansion and zero-velocity tests pass. Neither this test
nor the reduced contact count establishes mesh validity. Step convergence and
the effect of mapping a coarse triangle mesh still need separate verification.
The candidate is not enabled in the demo.

## Time-step and tessellation isolation

`scripts/inspect_atlas_flow_resolution.py` freezes the support radius from the
32-step result, compares 32/64 integration steps, and subdivides the source
triangles before applying the same field. Original vertices are retained and
their mapped positions are compared explicitly.

The first inspection exposed false positive contact reports on undeformed
subdivision children. The adjacent-triangle checker had treated all vertices
within the plane-distance tolerance as lying on a plane, expanding their
intersection interval. Its coplanar polygon clipping also expanded half-planes
by the tolerance. Both operations now compute geometric intersections before
applying the permitted shared-topology distance tolerance. This follows the
existing geometric-overlap contract; it is not a clearance-distance test.

A regression uses the actual near-coplanar source children sharing a midpoint.
Existing positive crossing and coplanar-overlap tests remain enabled.
**86 targeted tests pass** across the contact and atlas-edit modules.
The original inspection is preserved in `evidence/atlas-mca-flow-resolution.json`;
the corrected checker results are written separately to
`evidence/atlas-mca-flow-resolution-reviewed.json`, including the checker hash.

All four cases completed with the corrected checker:

| Source faces | Integration steps | Source contact pairs | Edited contact pairs |
|---:|---:|---:|---:|
| 800 | 32 | 0 | 6 |
| 800 | 64 | 0 | 6 |
| 3,200 | 32 | 0 | 0 |
| 12,800 | 32 | 0 | 0 |

Increasing steps changes the original vertex positions by at most
0.0004666006617901676 mm and does not remove coarse-mesh contacts. Subdivision
retains exactly the same transformed original vertices, while its new vertices
sample the nonlinear field between them. Both refined meshes have no detected
self-contact. Geometry hashes match the pre-checker-fix run at each resolution;
the checker change did not alter the deformation.

This supports coarse surface approximation as a contributor in this case.
It does not establish general injectivity or clinical validity. Refined meshes
still require checks against surrounding vessels, attachment surface retention,
and radius/containment constraints before app adoption. They are derived
surfaces; the original atlas mesh remains unchanged.

## Refined surface and surrounding arteries

The surroundings inspector supports a frozen subdivision comparison. It uses
the original contact protection regions, parameters, export fingerprint and
field support. Contacting source faces are followed through subdivision so the
new attachment-patch vertices are checked as well as the original vertices.

The level-one case (1,602 vertices / 3,200 faces) completed:

- All 517 other native arterial parts inspected; no unresolved pairs.
- No new or removed contacting vessels.
- Every before/after contacting triangle-pair ID set is unchanged.
- All 459 attachment-patch vertices exactly preserved, maximum movement 0 mm.
- No self-contact detected.
- Maximum boundary face-normal angle approximately 29.923 degrees; no new
  boundary pairs exceeding 90 degrees.

Evidence:
`evidence/atlas-mca-protected-edit-surroundings-width8-product-v3-polyline-flow32-subdiv1.json`.
These checks concern surface intersections and preservation of pre-existing
geometric contacts. They do not establish anatomical attachment correctness,
volume containment, true cross-sectional radius, or general editing validity.

The level-two case (6,402 vertices / 12,800 faces) also completed with no
self-contact, no unresolved surrounding comparisons, and unchanged contact
triangle-pair sets for all 517 other arteries. All 1,580 attachment-patch
vertices remain exactly fixed. This reproduces the level-one surface findings
at higher resolution.

Evidence:
`evidence/atlas-mca-protected-edit-surroundings-width8-product-v3-polyline-flow32-subdiv2.json`.
Neither inspection changes the live app. Further acceptance work is
cross-sectional radius/centerline containment and explicit derived-surface
provenance in the editing/export workflow, followed by broader vessel cases.

## Centerline containment and actual cross sections

`scripts/inspect_atlas_edit_sections.py` reconstructs the exact level-one
candidate and verifies both surface hashes before measurement. `rtree==1.4.1`
is declared for the trimesh ray containment query. Known-cylinder section and
inside/outside tests plus the existing section-metrics test pass (3 tests).

- Original and edited surfaces: **231/231 sampled centerline points inside**.
- Perpendicular sections: **229/229 non-endpoint samples measured** before and
  after, each with one closed contour enclosing its centerline point.
- Absolute difference between reported radius scale and measured area-equivalent
  radius scale: median 0.000011625, maximum **0.143177**.

At `FJ1692:e0`, index 153, the reported scale is **1.109913** while the measured
area-equivalent radius scale is **0.966735**. Stored radius changes from
1.447782 to 1.606911 mm; measured area-equivalent radius changes from 1.468932
to 1.420069 mm. Thus a reported local increase accompanies a measured decrease.
This is a material semantic mismatch, not a passing radius-accuracy result.
The global radius setting remains 1.3; local protection/taper makes the reported
local scale smaller.

Evidence: `evidence/atlas-mca-edit-sections.json` contains all section metrics and
sampled containment results. Section planes follow immediate path chords and
change with deformation. Neither the radius nor tangent is an independently
annotated anatomical reference. Sampled containment does not prove that every
intermediate point of the continuous path is inside.

Do not promote the candidate solely because collision checks pass. Correct
cross-section transport/radius semantics or explicitly separate requested scale
from independently measured resulting geometry before export acceptance.

## Measured-section radial correction experiment

`section_radius_correction.py` applies a positive interpolated gain around the
fixed edited centerline, with source-coordinate protection weights. The
experiment uses five predetermined iterations. Each iteration measures actual
sections and computes gain from target/measured area-equivalent radius. It does
not alter the requested radius parameter or the centerline.

| Iteration | Maximum relative error to local target | Self-contact pairs |
|---:|---:|---:|
| 0 | 12.900% | 0 |
| 1 | 7.559% | 8 |
| 2 | 5.417% | 9 |
| 3 | 3.937% | 9 |
| 4 | 2.912% | 9 |
| 5 | 2.498% | 10 |

Exactly fixed vertices remain fixed throughout. Radius-correction and section
measurement tests pass (7 tests). The actual correction candidate is **FAIL**
because self-contact reappears; lower radius error cannot override that failure.
No radius acceptance tolerance was introduced after seeing these results.
Surrounding-vessel contacts were not rerun on this failed candidate.

Evidence: `evidence/atlas-mca-section-correction.json`. The baseline flow
candidate, the source atlas, and the live workspace are preserved. This module
is experimental and is not connected to app editing or accepted export.
The development plan requires failed cases to remain separate from normal
data; this combination must not be labelled an accepted model.
