# Smoothed noncircular loft self-contact

The actual saved PLY artifacts were reloaded with processing disabled after
SHA256 verification. The existing finite-precision triangle contact checker
screened all distinct triangle pairs, including adjacent triangles for overlap
beyond shared topology. Tolerance was 1e-8 mm and the pair budget was 2,000,000
per candidate. Every candidate completed coverage without exhausting the budget.

| Edge | Narrow-phase pairs checked | Contact pairs |
|---|---:|---:|
| FJ1654:e0 | 40,992 | 91 |
| FJ1654M:e0 | 44,479 | 98 |
| FJ1660:e0 | 22,802 | 74 |
| FJ1660M:e0 | 22,853 | 111 |
| FJ1692:e0 | 60,440 | 0 |
| FJ1692M:e0 | 60,041 | 28 |
| FJ1694:e0 | 130,168 | 174 |
| FJ1694M:e0 | 129,980 | 116 |

Seven candidates are **CONTACT_DETECTED**; one is **NO_CONTACT_DETECTED**.
Neither status is a general vessel acceptance result. Other vessels,
open-end integration, junctions and anatomical validity are not checked.

## Localization

All detected pairs lie within the same longitudinal strip or strips one or two
stations apart. None of the detected pairs shares a full edge; some share one
vertex and the remainder have no shared vertex. Thus the result cannot be
explained solely by ordinary shared triangle edges. The pattern suggests local
overlap of adjacent profile strips, not remote vessel segments returning into
one another. Exact causes and continuous overlap geometry need further review.

The inspected data are the serialized PLY coordinates, including serialization
precision, rather than only the in-memory generator output. These numerical
predicates are not exact-arithmetic proof; the complete reported face pairs are
preserved for follow-up. The earlier improvement in source-distance samples
does not supersede these contact findings.

## State and reproduction

No candidate is promoted to the live Atlas. Original files and earlier
measurements remain unchanged. Repair must address local strip correspondence
or intersecting section planes and then repeat full contact screening; lowering
the distance threshold or ignoring neighboring pairs would not resolve this.

Regression: **26 passed** covering the contact predicates, shared-topology
handling, budget/degeneracy behavior and loft construction.

```text
python -m pytest tests/test_mesh_self_contact.py tests/test_adjacent_contact.py tests/test_triangle_contact.py tests/test_profile_loft.py -q
python scripts/inspect_cerebral_loft_contacts.py
```

- [Per-candidate contact pairs and coverage](evidence/cerebral-loft-self-contact.json)
- [Regression results](evidence/loft-contact-tests.xml)
