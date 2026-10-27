# Saved-case cerebral smoothing check

## Whole-interval numerical containment

All eight original paths and all eight smoothed paths passed a whole-interval
interior-ball coverage check: **533/533 intervals in each group**. The smallest
positive cover margin was 0.516578 mm for the source group and 0.532531 mm for
the smoothed group, after a 0.000001 mm numerical tolerance. These are numerical
clearance lower bounds, not vessel radii or clinical limits.

For each interval, the nearest-triangle distance at its midpoint must exceed
half the interval length plus tolerance, and the midpoint must classify inside.
Distance to a surface is 1-Lipschitz; under a valid closed-solid assumption,
the resulting interior ball covers the entire interval. Cells that do not
satisfy this bound are subdivided, an outside witness yields FAIL, and boundary
proximity or exhausted budgets yield UNKNOWN. All actual cohort intervals
passed without subdivision.

The checker is floating-point geometry, not exact arithmetic. Source surface
self-intersection and anatomical validity remain NOT RUN. The result concerns
centerlines only, not reconstructed tube walls, radius accuracy or route
acceptance. Exact-index copies preserve the source triangle coordinate bytes.

Regression: **11 passed**, including an inside path needing subdivision,
a case whose endpoints and initial midpoint are inside but intermediate
intervals exit, boundary contact, insufficient budget, genuinely open surfaces
and index-normalization cases.

- [Full interval evidence](evidence/cerebral-interval-containment.json)
- [Regression results](evidence/centerline-containment-tests.xml)
- Reproduce: `python scripts/inspect_cerebral_interval_containment.py`.

## Exact-index follow-up

All **8/8 edges passed sampled containment** after inspection-only exact
coordinate index normalization. All 3,117 original and 2,900 smoothed interval
samples were inside their corresponding unchanged triangle surfaces. This
supersedes the four unresolved *index-based containment* results below; it does
not approve anatomical boundaries or continuous containment.

The four initially non-watertight representations contain repeated vertices
at exactly equal coordinates:

| Part | Duplicate vertex excess | Raw boundary edges |
|---|---:|---:|
| FJ1654 | 11 | 30 |
| FJ1654M | 11 | 30 |
| FJ1694 | 6 | 22 |
| FJ1694M | 7 | 24 |

Combining only exact duplicate coordinates in a copy makes these meshes
watertight with consistent winding. The ordered triangle-coordinate bytes
remain identical. No triangle is added, removed or moved; no hole is capped.
The original files and indices are untouched. The other four meshes already
had watertight index topology.

`surface_indexing.exact_vertex_index_copy` records the method, zero tolerance,
triangle hash and index/topology diagnostics. Its tests include separated cube
indices, a truly missing face, near-but-not-equal coordinates and inconsistent
winding: **4 passed**. Genuine holes and near-coincident coordinates are not
silently closed. Self-intersection and anatomical validity remain NOT RUN.

Evidence:
- [Source topology audit](evidence/cerebral-source-surface-topology.json)
- [Eight-edge exact-index summary](evidence/workbench-cerebral-smoothing-summary-exact-indices.json)
- Detailed `*-exact-indices.json` files preserve the separate follow-up results.
- [Indexing tests](evidence/surface-indexing-tests.xml)

Reproduce inside the project Docker environment:
`python scripts/inspect_workbench_cerebral_smoothing.py --exact-indices`.

## Initial raw-index inspection

Eight explicit source edges were inspected with frozen workbench settings:
Gaussian width 0.5 mm, sampling interval 0.125 mm, and maximum displacement
0.3 mm. No failed edge was removed or retuned. The source snapshot is
`exports/atlas-case-inspection/all-arterial.snapshot.json`, SHA256
`fa2b9856bb47469b189af136c1e621f19381dd9470fca09f53e874061b9ff1cd`.

| Source edge | Maximum movement (mm) | Sampled surface containment |
|---|---:|---|
| FJ1654:e0 — right ACA | 0.212261 | UNKNOWN — raw index topology not watertight |
| FJ1654M:e0 — left ACA | 0.250735 | UNKNOWN — raw index topology not watertight |
| FJ1660:e0 — right MCA insular part | 0.238278 | PASS |
| FJ1660M:e0 — left MCA insular part | 0.227164 | PASS |
| FJ1692:e0 — right MCA sphenoid part | 0.177442 | PASS |
| FJ1692M:e0 — left MCA sphenoid part | 0.251132 | PASS |
| FJ1694:e0 — right MCA insular part | 0.242514 | UNKNOWN — raw index topology not watertight |
| FJ1694M:e0 — left MCA insular part | 0.240856 | UNKNOWN — raw index topology not watertight |

These are source-element names, not approved A1–A3/M1–M3 assignments. Multiple
elements have the same insular-part name and remain separate instances.

For all eight cases, original inputs, node coordinates, endpoint chords,
radius samples and unselected edges were preserved. Every movement stayed
within the declared bound. All 525 non-endpoint stations produced a unique
closed enclosing cross-section both before and after smoothing.

Containment used the unchanged source surface, original stations, and additional
points spaced at most 0.1 mm along each polyline interval. Four closed source
surfaces contained all tested original and modified points. Four open source
surfaces were not assigned an inside/outside classification. A missing
`outside_indices` result for these cases is not a zero-outside count.

The initial raw-index overall acceptance was **UNKNOWN**. Neither run proves continuous
containment, radius-to-surface accuracy, collision-free reconstructed tubes,
anatomical segment boundaries or a complete femoral–cerebral route. Original
non-watertight representations were not automatically capped. The follow-up
above distinguishes duplicate indices from missing triangle geometry.

The multi-edge audit also exposed derived case IDs that depended only on the
parent revision. The workbench now includes the selected edge and numerical
parameters in the deterministic ID digest, avoiding equal IDs for different
operations on one source. A regression checks repeatability and distinct
parameter IDs. Generated snapshots are stored under revision-specific folders;
earlier outputs are preserved.

## Evidence

- [Eight-edge summary](evidence/workbench-cerebral-smoothing-summary.json)
- [Right MCA detailed measurements](evidence/workbench-mca-smoothing.json)
- Other detailed measurements: `docs/evidence/workbench-smoothing-<edge>.json`.
- Each report records source/archive/surface hashes, result revision and path,
  containment samples, full section measurements and preservation checks.
- `scripts/inspect_workbench_cerebral_smoothing.py` reproduces the fixed cohort.
- Docker regression: **29 passed**, covering the workbench service, smoothing
  operator and preview logic; `docs/evidence/workbench-smoothing-tests.xml`.
