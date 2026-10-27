# Segment mask label registry

Case-based masks use `vv-toolbox.segment-label-registry/2`. The numeric
assignment is an output convention, not an anatomical boundary inference.

| Segment | Left | Right |
|---|---:|---:|
| ACA A1 | 1 | 7 |
| ACA A2 | 2 | 8 |
| ACA A3 | 3 | 9 |
| MCA M1 | 4 | 10 |
| MCA M2 | 5 | 11 |
| MCA M3 | 6 | 12 |
| Femoral, declared whole edge | 13 | 18 |
| External iliac, declared whole edge | 14 | 19 |
| Common iliac, declared whole edge | 15 | 20 |
| Common carotid, declared whole edge | 16 | 21 |
| Internal carotid, declared whole edge | 17 | 22 |

Midline access labels: abdominal aorta **23**, descending thoracic aorta **24**,
aortic arch **25**. Right brachiocephalic: **26**. Version 1's cerebral IDs
1–12 retain their meanings. These whole-edge labels do not specify finer ICA
subsegments or prove that an atlas fragment covers an entire anatomical vessel.

Zero remains unknown or conflicting anatomy, distinguished from background by
the foreground mask. Unsupported anatomy and missing/incomplete materialization
records remain zero.

`assign_access_labels(case, assignments, expected_revision=...)` accepts explicit
edge IDs, registry label IDs and full-extent evidence references. It returns a
copy and records the input revision and an edge fingerprint. No matching by
vessel name, proximity or route membership occurs. A subsequent change to the
edge ID, endpoints, centerline, radii or anatomy invalidates the declaration:
mask generation then uses zero until the extent is declared again. This is an
operator declaration, not independent anatomical approval. Source references
are recorded but not automatically authenticated.

The access declaration API, saved-case web screen and case-mask integration are
implemented. Atlas extent annotation, direct selection on the main Atlas surface and automatic
review-preserving propagation through geometry edits remain outstanding.

## Saved-case web screen

Open `/case-labels` from **5 · Source case data → Label a saved case**.
Upload a snapshot (maximum 16 MB), filter edges by name/side/ID, select a label,
provide full-extent references, apply to the copy and download the result.
The service checks snapshot integrity and never writes case files on the server.
It neither changes the Atlas scene nor certifies the declared vessel extent.
The UI requires explicit label selection for previously unlabelled edges.
The tab retains up to 20 label revisions for Undo/Redo. A new edit after Undo
discards the redo branch. Invalid uploads preserve the loaded case and history;
replacing a case with changes not yet downloaded requires confirmation.
Undo restores the complete snapshot, not just its displayed label. History is
local to the open tab and is not embedded in downloaded snapshots.

Verification: **25 tests passed** across the workbench service, source-case
service and access-label CLI. Browser verification used a synthetic two-edge
fixture on the running port 8093: upload, filtering, no-match disabled action,
missing-reference rejection, label application, downloaded content and mobile
layout. No page/console errors were observed. The saved user Atlas-edit
snapshot hash remained unchanged. Evidence:
`docs/evidence/label-workbench-tests.xml` and
`docs/evidence/label-workbench-browser.json`.

Browser plugin was unavailable; the frontend-testing-debugging skill's
Playwright fallback used the existing browser connection. Screenshots are
local inspection artifacts under `exports/label-workbench/`.

### Centerline preview

The saved-case screen renders its centerlines with orthographic projection.
Drag or arrow keys rotate, wheel zooms, **Focus selected edge** fits one edge,
and **Reset view** restores the full case. Clicking a line selects its edge in
the label controls; selection in the list highlights it in cyan. Red lines are
context centerlines, not reconstructed lumen surfaces. Projection overlaps can
be ambiguous; rotate and verify the displayed instance ID. Missing centerlines
are omitted and the rendered/total count is displayed.

The actual saved arterial Atlas snapshot (8,523,589 bytes, 1,081 edges) loaded
successfully and `FJ1692:e0` was selected by search. The upload cap was raised
from 4 MiB to 16 MiB to admit this full case; HTTP request cap is 20 MiB for
this endpoint only. This is display evidence, not anatomical acceptance.

The first full-atlas browser attempt exposed a hash mismatch when JavaScript
re-serialized Python float spellings such as `1.0` and `-0.0`. The browser now
preserves the server's serialized snapshot separately from display data,
uses that exact string for subsequent operations and downloads, and verifies
the incoming revision before processing. A regression checks float and
negative-zero preservation through apply/download.

**17 tests passed** for projection/picking, focus/reset, data immutability,
label service and CLI integration. Real-browser synthetic checks also passed
click selection and keyboard rotation. Full Atlas load/selection screenshots
and evidence: `docs/evidence/case-preview-atlas-browser.json`;
unit evidence: `docs/evidence/case-preview-tests.xml`.

### Recorded endpoint relationships

The saved-case screen shows every other edge incident to the selected edge's
first and last node, with no neighbor-count truncation. Each column includes
the node kind and evidence status; neighbor buttons include their edge evidence
and select/focus that edge. First/last denotes centerline point order, not
upstream/downstream blood flow. Equal coordinates with different node IDs do
not create a connection. An empty list is not presented as an anatomical
terminal unless the node explicitly carries that declaration.

The browser fixture has five neighbors at each end plus a geometrically
coincident, separately identified node. Both columns retained all five,
excluded the unrelated coincident edge, displayed unresolved node evidence,
and supported neighbor selection and return. Mobile retained all ten buttons
without horizontal overflow. The existing edit/undo/download browser flow also
passed. Evidence: `docs/evidence/case-relationships-browser.json`. This verifies
saved-graph incidence presentation only; missing or uncertain Atlas connections
remain missing or uncertain.

### Selected-centerline smoothing

**Modify selected centerline** invokes the existing arc-length Gaussian operator
on one edge of a separate synthetic copy. Original source content is preserved.
The first two and last two centerline points, all node positions and radii stay
fixed. Other edges remain unchanged. Existing lesion edges, closed paths and
paths with fewer than five points are rejected.

Interactive engineering limits are sigma 0.05–5 mm, displacement >0 and <=10 mm,
spacing sigma/4, and at most 50,000 resampling points. These are numerical and
runtime limits, not clinical ranges. Exceeding the declared displacement rejects
the edit without changing the current case. The generated snapshot records the
parent revision and measured displacement. Geometry quality remains NOT RUN,
anatomical acceptance UNKNOWN; no surface collision test is implied. Changed
geometry invalidates geometry-bound access-label declarations until re-reviewed.

Undo/Redo restores the full geometry snapshot and refreshes the preview.
Downloads preserve the server's canonical JSON. **29 tests passed**, covering
the service, underlying smoothing operator and preview. The browser fixture
measured maximum displacement **0.093057 mm** under a 0.3 mm bound; endpoints,
endpoint chords, radii and other edges were unchanged. Undo downloaded the exact
source and redo downloaded the exact result. The downloaded result also passed
the case CLI's structure/hash inspection.

Evidence: `docs/evidence/workbench-smoothing-tests.xml` and
`docs/evidence/workbench-smoothing-browser.json`. This is synthetic fixture
verification, not acceptance of smoothing across all real Atlas vessels.

Undo/Redo browser follow-up passed on port 8093: an undone download equals the
original fixture snapshot, redo restores the applied label, a new edit clears
redo, malformed uploads and cancelled replacement preserve the current edit,
and the final downloaded snapshot contains the selected label. Desktop and
mobile screenshots were refreshed; no page/console errors were observed.

## Saved-case commands

`vv-case label-registry` prints the complete ID table. `vv-case inspect source.json`
prints the source revision to bind in a request. An access request has this form
(the digest and edge ID must be taken from the actual source):

```json
{
  "schema": "vv-toolbox.access-label-request/1",
  "source_case_revision": "<revision from inspect>",
  "assignments": [
    {
      "edge_id": "<explicit edge ID>",
      "label_id": 13,
      "evidence_refs": ["<reference covering the entire declared edge extent>"]
    }
  ]
}
```

Apply it with `vv-case access-labels source.json labels.json labelled.json`.
The destination must be new and different from both inputs. Stale revisions,
duplicate JSON keys, invalid IDs and missing references are rejected. The
command reports `anatomical_acceptance=UNKNOWN`; it does not upgrade the
case's anatomical evidence status.

The labelled snapshot can be passed to `vv-case batch`. A candidates file
containing `[[]]` requests unchanged baseline reconstruction. For example:

```text
vv-case batch labelled.json candidates.json output --target-count 1 --max-attempts 1 --seed 3 --spacing-mm 0.3 --mask-config grid.json
```

Grid spacing, origin and shape must be chosen for the actual case frame and
cover its surface. CLI integration evidence is recorded in
`docs/evidence/access-label-cli-tests.xml`. These commands operate on saved
cases; they do not alter the running atlas viewer.

CLI follow-up: **33 passed**, 60 upstream deprecation warnings, across
`test_access_labels_cli`, `test_anatomical_labels`, `test_case_io` and
`test_volume_cli`. The end-to-end CLI fixture applies L/R femoral labels,
reconstructs the baseline through `batch`, and reads back IDs 13/18 and an
all-zero lesion array from the exported NPZ.

Case mask generation checks the edge's side, artery and segment against the
registry. Cerebral nonzero values require structural materialization references:
original edge, interval, tolerance, boundary IDs and full-extent review
references. These fields are not independently verified clinical annotations.
Callers may explicitly suppress a label to zero but cannot replace it with an
arbitrary or opposite-side ID.

The registry, schema, hash and evidence scope are stored in NPZ volume metadata
and case mask quality results. Whole volumes and lesion ROIs use the same
mapping. Crop copies preserve an independent registry copy. Low-level
`voxelize` inputs remain explicitly caller-labelled; this registry policy applies
to case-based masks.

## Verification

Docker tests:

```text
python -m pytest tests/test_anatomical_labels.py tests/test_batch.py tests/test_voxel_output.py tests/test_volume_cli.py tests/test_segment_materialization.py -q
```

**52 passed**, 70 upstream NumPy/scikit-image deprecation warnings.
Machine-readable result: [access-label-tests.xml](evidence/access-label-tests.xml).
Coverage includes the 12 retained cerebral IDs and 14 access labels, input-order
independence, wrong-side and invalid-label rejection, unmaterialized labels
staying zero, stale geometry/extent rejection, input immutability, end-to-end
batch NPZ left/right A2 values, saved left/right femoral mask values, registry
persistence, and crop metadata independence. Full-suite and browser verification
of this API addition have not been run.

The access-mask fixture declares labels after synthetic lesion generation;
it checks output mechanics, not the clinical consistency of lesion-region
settings with reassigned vessel anatomy. Cases without declared lesions now
produce an all-zero lesion mask with `lesion_presence=none_declared` and
`sampling_status=NOT APPLICABLE`. This means no lesion was declared in the
synthetic case; it does not certify a source specimen as clinically healthy.

An empty candidate (`[[]]` as the candidate pool) requests baseline
reconstruction without new lesions in the batch API. The copied case is marked
synthetic, records its parent revision and generation seed, and preserves its
centerlines, radii, annotations and any pre-existing lesions. It passes through
the same surface and mask checks. Distribution summaries count baseline
candidates separately from malformed input. A lesion ROI still requires known
target lesions. Evidence: `docs/evidence/healthy-mask-tests.xml`.

Healthy/baseline output follow-up: **57 passed**, 79 upstream deprecation
warnings, using `test_lesion_labels`, `test_anatomical_labels`, `test_batch`,
`test_batch_distribution`, `test_voxel_output`, and `test_volume_cli`.
This includes whole-mask NPZ export with and without lesions, preservation of
pre-existing lesions for a baseline candidate, and rejection of unknown lesion
targets, invalid mappings and insufficient memory budgets. This run does not
establish anatomical correctness or validate a new application UI.

These are synthetic software fixtures. They do not resolve the outstanding
real-atlas cerebral boundary annotations or certify anatomical ground truth.
