"""Declare a synthetic graph from inspected links and probe four access pairs."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.access_routes import inspect_route
from vv_toolbox.case_io import case_digest, load_case, save_case
from vv_toolbox.declared_sample_graph import build_declared_sample_graph


def main():
    root = Path("docs/evidence")
    read = lambda name: json.loads((root / name).read_text())
    proposals = read("access-path-link-candidates.json")
    coincident = read("access-coincident-link.json")
    paths = read("femoral-anterior-paths.json")
    case, revision = load_case(read("atlas-neck-volume-case.json")["derived_case_file"])
    surface = Path("exports/femoral-anterior-union/candidate.npz")
    digest = hashlib.sha256(surface.read_bytes()).hexdigest()
    for record in (proposals, coincident, paths):
        if record["source_case_revision"] != revision or record["union_sha256"] != digest:
            raise ValueError("Inspection identity mismatch")
    if paths["status"] != "PASS" or coincident["status"] != "PASS":
        raise ValueError("Completed path and coincident-point inspections required")
    original = {e["id"]: e for e in case["edges"]}
    for row in paths["rows"]:
        points = np.asarray(original[row["edge_id"]]["centerline_mm"], dtype="<f8")
        if hashlib.sha256(points.tobytes()).hexdigest() != row["path_sha256"]:
            raise ValueError("Inspected path changed")
    declarations, chosen = [], {}
    for pair in proposals["rows"]:
        options = [c for c in pair["candidates"] if c["containment"]["status"] == "PASS"]
        evidence = "docs/evidence/access-path-link-candidates.json"
        if not options and (pair["first_part"], pair["second_part"]) == ("FJ3466", "FJ3464"):
            options = [c for c in pair["candidates"] if c["distance_mm"] == 0
                       and c["points_mm"][0] == coincident["coordinates_mm"] == c["points_mm"][1]]
            evidence = "docs/evidence/access-coincident-link.json"
        if not options:
            raise ValueError("No inspected candidate for declared adjacency")
        selected = min(options, key=lambda c: (c["distance_mm"], c["first_edge"], c["second_edge"],
                                               c["first_index"], c["second_index"]))
        for prefix, point in zip(("first", "second"), selected["points_mm"]):
            if original[selected[prefix+"_edge"]]["centerline_mm"][selected[prefix+"_index"]] != point:
                raise ValueError("Link anchor changed")
        index = len(declarations)
        declarations.append({**{k: selected[k] for k in ("first_edge", "first_index", "second_edge", "second_index")},
                             "containment_status": "PASS", "evidence_ref": evidence})
        chosen[frozenset((pair["first_part"], pair["second_part"]))] = (index, selected)
    edge_ids = [r["edge_id"] for r in paths["rows"]]
    result = build_declared_sample_graph(case, edge_ids, declarations,
        case_id="femoral-anterior-declared-sample-graph", expected_revision=revision)
    result["generation"]["config"]["selection_policy"] = "Shortest contained sampled link per explicit adjacency; lexical tie break"
    result["candidate_surface_reference"] = dict(file=str(surface), sha256=digest,
                                                radius_envelope="NOT RUN", junction_smoothness="NOT RUN")
    by_id = {e["id"]: e for e in result["edges"]}
    for eid, fragment_ids in result["declared_sample_graph"]["fragments"].items():
        points, radii = [], []
        for index, ident in enumerate(fragment_ids):
            points.extend(by_id[ident]["centerline_mm"][1 if index else 0:])
            radii.extend(by_id[ident]["radii_mm"][1 if index else 0:])
        if points != original[eid]["centerline_mm"] or radii != original[eid]["radii_mm"]:
            raise ValueError("Source samples or radii changed")
    folder = Path("exports/femoral-anterior-graph")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "case.snapshot.json"
    derived_revision = case_digest(result)
    if target.exists():
        if load_case(target)[1] != derived_revision:
            raise ValueError("Existing graph differs; refusing overwrite")
    else:
        save_case(target, result)
    if load_case(target)[0] != result:
        raise ValueError("Graph roundtrip mismatch")

    aliases = result["declared_sample_graph"]["node_aliases"]
    def canonical(node):
        while node in aliases:
            node = aliases[node]
        return node

    routes = []
    for leg, leg_parts in (("L", ["FJ2074", "FJ3466", "FJ3464"]),
                           ("R", ["FJ2143", "FJ3567", "FJ3565"])):
        femoral = original[leg_parts[0]+":e0"]
        start = canonical(min((femoral["start"], femoral["end"]),
                              key=lambda n: case["nodes"][n]["position_mm"][2]))
        for head, head_parts, suffix in (("L", ["FJ3483", "estimated_left_carotid_neck", "FJ1682M"], "M"),
                                        ("R", ["FJ3417", "FJ3564", "estimated_right_carotid_neck", "FJ1682"], "")):
            for artery in ("FJ1654", "FJ1692"):
                terminal = artery+suffix
                sequence = leg_parts + ["FJ1932", "FJ1931", "FJ3411"] + head_parts + [terminal]
                required = []
                for a, b in zip(sequence, sequence[1:]):
                    index, link = chosen[frozenset((a, b))]
                    if link["distance_mm"] > 0:
                        required.append(f"declared-link:{index}")
                _, attachment = chosen[frozenset((head_parts[-1], terminal))]
                edge = original[attachment["second_edge"]]
                points = np.asarray(edge["centerline_mm"])
                cumulative = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
                at = cumulative[attachment["second_index"]]
                end = canonical(edge["start"] if at >= cumulative[-1]-at else edge["end"])
                route = inspect_route(result, start, end, required)
                routes.append(dict(femoral_side=leg, carotid_side=head, target=terminal,
                                   start=start, end=end, required_edges=required, **route))
    report = dict(status="PASS" if all(r["status"] == "PASS" for r in routes) else "UNKNOWN",
                  source_revision=revision, derived_revision=derived_revision, surface_sha256=digest,
                  graph_file=str(target), selected_source_edges=len(edge_ids),
                  graph_edges=len(result["edges"]), graph_nodes=len(result["nodes"]),
                  source_polyline_samples_preserved=True,
                  declarations=result["declared_sample_graph"]["declarations"], routes=routes,
                  scope="Four femoral/carotid pairs to registered ACA and proximal MCA paths; not A3/M3 coverage",
                  source_anatomical_evidence_upgraded=False, live_scene_changed=False,
                  junction_smoothness="NOT RUN", radius_envelopes="NOT RUN")
    (root / "access-sample-graph.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "selected_source_edges", "graph_edges", "graph_nodes")}), flush=True)
    for route in routes:
        print(json.dumps({k: route[k] for k in ("femoral_side", "carotid_side", "target", "status", "edges")}), flush=True)


if __name__ == "__main__":
    main()
