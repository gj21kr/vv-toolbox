# Simultaneous protected cerebral replacement inspection

All eight serialized protected candidates were substituted simultaneously in
an inspection-only copy of the original 518-part arterial scene. Candidate
SHA256, unchanged face-index arrays, protected coordinates and Atlas archive
identity were verified before comparison. The live scene and original files
were not changed.

## Complete affected-pair coverage

| Measure | Result |
|---|---:|
| Original arterial parts | 518 |
| Simultaneous replacement parts | 8 |
| Affected unordered part pairs | 4,108 |
| Separated bounds both before and after | 4,038 |
| Detailed original/candidate triangle comparisons | 70 |
| Contacting part relations before / after | 36 / 36 |
| Added contact triangle pairs | 0 |
| Lost contact triangle pairs | 0 |

All detailed checks completed without budget exhaustion. Every affected pair
was examined, including all 28 candidate-to-candidate combinations: six required
detailed comparison and 22 were bounds-separated. Pairs of two untouched source
parts were not rechecked because neither geometry changed.

For each detailed relation, exact face-ID pairs were compared on the unchanged
face-index topology, rather than only comparing contact counts or names.
The original numerical surface-contact pair set was preserved across all
affected pairs at the fixed 1e-8 mm tolerance.

## Scope

This establishes preservation of the detected surface-contact pair sets under
the same numerical checker. It does not approve the original contacts as
anatomical junctions, establish connected lumen openings, exclude complete
volume containment, or verify source-derived centerline/radius consistency.
Anatomical segment boundaries and full femoral-to-cerebral routes remain
separate work.

Together with the prior complete self-contact screening and serialized
protected-coordinate checks, this provides evidence for a clearly labeled
source/candidate comparison preview. It is not authorization to overwrite the
original reference model or a claim of clinical validity.

```text
python scripts/inspect_protected_cerebral_scene.py
```

[Complete pair coverage and face-pair comparison evidence](evidence/protected-cerebral-scene.json)
