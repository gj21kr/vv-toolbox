# Bilateral iliofemoral source inspection

Both declared external-iliac–femoral transitions were inspected in the original shared source coordinates. **Inspection is complete; both connections remain unresolved.** No continuation bridge specification was issued, because the source endpoint directions oppose the proposed gap direction and no terminal boundary ring was identified.

## Source correspondence

The endpoint inventory, original arterial case, loaded atlas archive and synthetic arch–carotid parent were checked for matching source identities. The four target edges in the parent are identical to their source counterparts. The parent revision is recorded in [the evidence report](evidence/iliofemoral-gaps.json); input source and parent bytes remained unchanged.

| Side | Distal external iliac extraction endpoint | Proximal femoral extraction endpoint | Endpoint chord (mm) |
| --- | --- | --- | ---: |
| L | `FJ3466:e0.end` | `FJ2074:e0.start` | 30.156923 |
| R | `FJ3567:e0.start` | `FJ2143:e0.end` | 24.592682 |

These are numerical centerline-extraction endpoints, selected from the named source parts and superior/inferior courses. They are not identified arterial openings or an inguinal-ligament transition. Nearest endpoint matching was not used to establish anatomy.

## Actual surface observations

All original mesh outline paths were retained and measured: left external iliac 3, left femoral 1, right external iliac 6, right femoral 2. All have essentially zero projected area (largest approximately 1e-14 mm²), consistent with degenerate/backtracking outline paths. None meets the fixed nondegenerate planar transverse terminal-opening criteria. The algorithm therefore does not assign an opening center.

The figures display actual source triangles within 45 mm of the extraction endpoints, source centerline portions and the endpoint chord. Five planes perpendicular to that chord sample fractions 0, 0.25, 0.5, 0.75 and 1. Their source-section polylines and coordinates are preserved in the report. These show adjacent source courses; they do not demonstrate a simple empty lumen gap between two facing open ends. No mesh repair, coordinate shift or fabricated tube was applied.

The outward direction measured over the last 5 mm of each centerline points away from the other endpoint:

| Side | External iliac angle to other endpoint | Femoral angle to other endpoint |
| --- | ---: | ---: |
| L | 142.179° | 144.172° |
| R | 171.716° | 171.751° |

Last-chord angles are likewise opposing: L 151.839°/151.839°, R 151.972°/171.530°. A tangent-preserving endpoint bridge would need to turn back toward its destination. No numerical handle choice was used to hide this conflict.

Distances from extraction endpoints to the opposite actual surface are L 15.322530/4.632508 mm and R 2.663479/2.851386 mm (external iliac/femoral respectively). These are unsigned point-to-triangle distances, not lumen clearance or proof of anatomical continuity. Their exact witness coordinates and triangle indices are recorded.

## Outputs and next decision

- [Inspection evidence](evidence/iliofemoral-gaps.json)
- `exports/iliofemoral-gaps/l-source-openings.png`
- `exports/iliofemoral-gaps/r-source-openings.png`

Both figures were viewed after generation. The top-level `extension_specification` is explicitly `null`. The report binds the inspected parent revision, but does not authorize any connection.

Next work must identify a justified transition within the source courses, including their overlap/coordinate relationship and the anatomical external-iliac–femoral boundary, before choosing an interior cut or connector. This requires a different attachment decision; it is not solved by snapping extraction endpoints. Anatomical acceptance remains **UNKNOWN** and no app change was made.

Reproduce using the project container:

```text
docker exec -e PYTHONPATH=src vv-annotation-ui python scripts/inspect_iliofemoral_gaps.py
```
