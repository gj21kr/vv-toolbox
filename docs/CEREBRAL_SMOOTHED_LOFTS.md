# Fixed smoothed-path profile loft comparison

## Diagnostic finding

In the original `FJ1694:e0` path, station 43 has section area 12.2391 mm²,
compared with 4.7099 mm² at 42 and 4.3372 mm² at 44. Its area centroid moves
away from the station, and the local chord direction changes sharply. This
suggests sensitivity of section selection to the extracted zigzag path, rather
than evidence that the source surface itself should be replaced by a bulge.

The existing frozen smoothing configuration (sigma 0.5 mm, displacement bound
0.3 mm) was used without per-edge parameter changes. Profiles were re-extracted
from the same original triangles at those previously saved smoothed paths;
the same 64-point perimeter loft method was applied. Both section origins and
normals change, so this comparison does not isolate their individual effects.
All 525 interior profiles remained MEASURED; none was dropped.

## Comparison

Largest original-surface distance among all candidate triangle centroids:

| Edge | Original path (mm) | Smoothed path (mm) |
|---|---:|---:|
| FJ1654:e0 | 0.095393 | 0.070017 |
| FJ1654M:e0 | 0.106777 | 0.092935 |
| FJ1660:e0 | 0.047148 | 0.030694 |
| FJ1660M:e0 | 0.036563 | 0.030251 |
| FJ1692:e0 | 0.058831 | 0.039667 |
| FJ1692M:e0 | 0.049687 | 0.052817 |
| FJ1694:e0 | 1.081462 | 0.088214 |
| FJ1694M:e0 | 0.279930 | 0.060439 |

Seven maxima decrease and one increases. All eight p95 distances decrease.
The right MCA worst sampled error moves from station pair 43–44 to 40–41.
This is a frozen comparison, not a new acceptance threshold. Finite one-way
samples do not bound continuous surface error or prove preserved anatomy.

## Artifacts and scope

Source-case revision and per-edge smoothed-case revisions are separately
recorded and checked. Original profile/loft artifacts and reports are retained.
New content-addressed profiles and PLY surfaces are separate candidates.
The live Atlas model is not replaced.

Candidates still have two open interior boundaries; endpoint integration,
junctions, continuous and bidirectional surface-error bounds, self-intersection
and neighboring-vessel collision remain unverified. A smoother frame alone is
not a completed vessel reconstruction.

```text
python scripts/extract_cerebral_source_sections.py --smoothed
python scripts/inspect_cerebral_profile_lofts.py --smoothed
```

- [Smoothed profile records](evidence/cerebral-smoothed-section-profiles.json)
- [Smoothed loft measurements](evidence/cerebral-smoothed-profile-lofts.json)
- [Original loft comparison](CEREBRAL_PROFILE_LOFTS.md)
