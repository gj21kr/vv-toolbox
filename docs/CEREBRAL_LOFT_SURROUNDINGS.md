# Window-profile candidates against surrounding arteries

Each of the eight serialized 2 mm-window candidates was checked against all
**517 other original arterial parts** in the same registered Atlas frame.
The declared source part alone was excluded from its own comparison.
Original archive, profile binding and serialized candidate hashes were checked.

Of **4,136 candidate-to-source comparisons**, 4,069 were separated by conservative
axis-aligned bounds (expanded by the same 1e-8 mm tolerance), and 67 received
triangle-pair screening. All 67 completed; no pair budget was exhausted.

| Candidate | Bounds-overlap comparisons | Contacting original parts |
|---|---:|---|
| FJ1654:e0 | 7 | FJ1655, FJ1676, FJ1682, FJ1690 |
| FJ1654M:e0 | 8 | FJ1655, FJ1662M, FJ1682M, FJ1690M, FJ1692M |
| FJ1660:e0 | 4 | FJ1692 |
| FJ1660M:e0 | 4 | FJ1692M |
| FJ1692:e0 | 12 | FJ1660, FJ1682, FJ1718 |
| FJ1692M:e0 | 12 | FJ1660M, FJ1682M, FJ1718M |
| FJ1694:e0 | 10 | FJ1664, FJ1716 |
| FJ1694M:e0 | 10 | FJ1664M, FJ1716M |

There are **21 contacting candidate-to-original relations**. For every one,
the corresponding original-to-original surfaces also had contact, with complete
pair screening. No newly contacting part combination was found within this
surface-intersection scope.

## Interpretation

All eight candidates remain CONTACT_DETECTED against their surroundings.
Existing source contact is not an exemption or an anatomical junction approval.
The comparison does not prove that contact location, extent, branch opening,
flow continuity or topology was preserved. Those require explicit junction
correspondence and local geometric verification.

The candidates have open interior boundaries. Surface-intersection screening
does not exclude complete volume containment. Simultaneous candidate-to-candidate
contacts, veins, organs and clinical anatomy are outside this run.
The 21 results are directional candidate-to-original relations, not 21 distinct
unordered anatomical vessel pairs.

The complete face-pair evidence and original baselines are retained; original
surfaces and the live Atlas scene remain unchanged.

## Reproduction

Contact-kernel regression: **8 tests passed**.

```text
python -m pytest tests/test_mesh_pair_contact.py tests/test_triangle_contact.py -q
python scripts/inspect_cerebral_loft_surroundings.py
```

- [Full coverage, face pairs and source baselines](evidence/cerebral-loft-surroundings-window2mm.json)
- [Regression tests](evidence/loft-surroundings-tests.xml)
