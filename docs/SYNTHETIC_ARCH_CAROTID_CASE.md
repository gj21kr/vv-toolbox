# Synthetic arch–left carotid candidate

The inspected aortic arch anchor is connected to the left common carotid artery in a separate synthetic snapshot. Graph construction and preservation checks pass; surface generation is blocked by two nonincident capsule-contact candidates. This candidate is **NOT ACCEPTED** for default use. Anatomical connection remains **UNKNOWN**.

## Inputs and explicit construction

- Parent: `exports/synthetic-neck-case/case.snapshot.json`, revision `165cebe813b506cf1a12bd299de0b05c96890def6214e4233d85d33e3eea55b3`.
- Anchor evidence: [arch-carotid-junction.json](evidence/arch-carotid-junction.json). Source archive, centerline-preview and original case hashes are checked against the parent before construction.
- Split `FJ3411:e0` at interval 32, fraction `0.3576715787251739`, position `[17.08613726298014, -100.51386273701988, 1305.6000000000001]` mm. The full parent edge is archived, with two derived children retaining its geometry and interpolated boundary radius.
- Create `estimated_arch_to_LCCA` from the split node to `FJ3483:e0.start`. The departure direction is the inspected opening-center position minus the anchor, not the arch tangent. The declared branch radius is 4 mm; the arch radius at the anchor is 11.6048632814 mm. This intentional radius difference is not a continuation-radius discontinuity.
- Both Hermite handles equal the endpoint chord length, 5.6308018475 mm, with 96 samples. These are fixed numerical modeling choices, not anatomical measurements or clinically validated settings.

The inspected opening center selects the initial direction; the Hermite curve is not constrained to pass through that center. The anchor inspection does not establish a clinically exact ostium.

## Measured results

The derived revision is `2b77c5e97f7d7b6c51625b82bb5c8ef7165fb12eb3979a64c2a15646d9c264ae`. Snapshot round-trip, unchanged parent bytes, preserved unrelated edges, archived full parent arch, and the three incident edges at `synthetic_arch_LCCA_origin` were checked successfully.

The declared graph traversal reaches arch → LCCA → estimated neck connection → ICA. Route evidence remains **UNKNOWN**, because underlying source nodes/edges remain unresolved; graph reachability does not promote anatomical certainty.

All six bridge attachments pass the sampled centerline check at fixed numerical tolerances of 5° and 0.000001 mm radius jump. For the new branch, endpoint position and declared radius gaps are zero; sampled tangent differences are 0.548102° at the arch and 0.173667° at the CCA. The start comparison uses the explicit branch direction and radius, not the parent arch radius or tangent. Surface smoothness remains **NOT RUN**.

The selected six-edge surface attempt at 0.6 mm spacing fails closed with `nonincident vessel clearance unresolved; surface union blocked`. The same selected-edge capsule screen checks 1,226 interval pairs and separates seven edge pairs by bounding boxes. It records the first witness for each of two potentially contacting edge pairs:

| Edge pair | Interval indices | Clearance lower bound (mm) |
| --- | --- | ---: |
| `synthetic_arch_before_LCCA` / `FJ3483:e0` | 17 / 0 | -0.590912 |
| `synthetic_arch_after_LCCA` / `FJ3483:e0` | 0 / 0 | -10.047117 |

The report includes the exact witness endpoint coordinates, radii and source-part identity. These are conservative capsule bounds and first witnesses, not measured surface penetrations or pairwise minimum distances. The CCA and arch children do not directly share a node because the explicit bridge lies between them. Their large-radius envelopes overlap near the attachment, so the current nonincident rule blocks their union. No radius, collision margin, or exemption was adjusted to obtain a surface. No surface artifact was published.

## Artifacts and reproduction

Run inside the project container:

```text
docker exec -e PYTHONPATH=src vv-annotation-ui python scripts/build_synthetic_arch_carotid_case.py
```

- [Machine-readable evidence](evidence/synthetic-arch-carotid-case.json)
- `exports/synthetic-arch-carotid-case/split-specification.json`
- `exports/synthetic-arch-carotid-case/extension-specification.json`
- `exports/synthetic-arch-carotid-case/split-case.snapshot.json`
- `exports/synthetic-arch-carotid-case/case.snapshot.json`
- `exports/synthetic-arch-carotid-case/arch-carotid-candidate.png`

The figure was inspected: it shows the declared centerline graph and attachment direction in a sagittal projection, not a validated fused surface. Generated snapshots/specifications and the figure remain under ignored `exports/`; the inspection report is tracked as evidence. Existing differing snapshots are rejected rather than overwritten.

Next work requires an explicit junction-region treatment that distinguishes intended local branch union from remote vessel collisions, with bounded geometric evidence. Whole-case collision, final surface collision, femoral access combinations and anatomical approval are not established by this experiment. Source geometry and the app remain unchanged.
