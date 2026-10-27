# Bounded synthetic junction regions

`inspect_junction_regions(case, edge_ids, regions, margin_mm=0, max_segment_pairs=1000000)` screens every distinct pair of selected edges, including incident pairs. It operates only on synthetic cases and does not modify geometry or existing clearance functions.

Each region declares `id`, `case_sha256` (the exact current case digest), `root_node_id`, nonempty `rationale`, nonempty `evidence_refs`, and `portions`. A portion has `edge_id`, `endpoint` (`start` or `end`) and positive physical `length_mm` measured inward along that edge. Each edge appears at most once per region. Portions must form one connected region through their included graph nodes, rooted at the declared node.

Ordinary regions require at least two unconsumed external arms. A fully included edge is allowed only when it is registered in `synthetic_route_inspection.bridge_ids`, declares `derivation.attachment_mode = side_branch`, has both endpoints of region incidence at least two, and the region has at least three unconsumed external arms. This permits a short explicit branch bridge between parent arms and a daughter arm. It does not permit consuming an external arm or silently adding disconnected obstacles to an exemption.

All intervals are split exactly at physical extent boundaries, interpolating position and radius. A pair is exempt only when **both complete clipped intervals** lie inside the same declared region. Inside–outside and outside–outside pairs remain checked. Each clipped interval is bounded by a capsule using the larger endpoint radius. Every edge pair retains its first potential-contact witness, with clipped arc intervals and endpoint coordinates; this is not the global minimum clearance.

`PASS` certifies only the tested conservative capsules outside the explicit regions. Potential contact or exhausted pair budget returns `UNKNOWN`. The budget counts checked and exempt interval pairs. Regions themselves remain `NOT CHECKED`, within-edge self-intersections and final surface collisions remain `NOT RUN`, and anatomical acceptance remains `UNKNOWN`. Declaration connectivity is a graph property, not proof that an allowance is anatomically appropriate or geometrically safe.

The caller must justify and record extent selection before accepting any generated surface. Existing nonincident, junction-collar and self-clearance functions retain their original behavior. This inspector provides no automatic repair or anatomy promotion.

Different regions cannot overlap or touch on the same edge; opposite endpoint prefixes must leave a positive unexempted interval. Returned declarations are deep-copied so subsequent caller edits cannot alter recorded provenance. The final focused Docker run passed 22 junction-region tests; together with the existing geometry-quality tests, 48 tests passed.

Focused synthetic tests cover internal bridge allowance, ordinary degree-two junctions, preservation, remote recrossing, coarse-interval clipping, inside–outside contact, unrelated-edge collisions, malformed/disconnected declarations, source-case rejection and exhausted budgets.
