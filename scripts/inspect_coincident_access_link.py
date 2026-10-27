"""Review the zero-length left iliac proposal without merging graph nodes."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case


def main():
    root = Path("docs/evidence")
    links = json.loads((root / "access-path-link-candidates.json").read_text())
    case, revision = load_case(json.loads((root / "atlas-neck-volume-case.json").read_text())["derived_case_file"])
    surface = Path("exports/femoral-anterior-union/candidate.npz")
    if revision != links["source_case_revision"] or hashlib.sha256(surface.read_bytes()).hexdigest() != links["union_sha256"]:
        raise ValueError("Link evidence identity mismatch")
    pair = next(r for r in links["rows"] if (r["first_part"], r["second_part"]) == ("FJ3466", "FJ3464"))
    if len(pair["candidates"]) != 1:
        raise ValueError("Unique coincident proposal required")
    candidate = pair["candidates"][0]
    if candidate["distance_mm"] != 0:
        raise ValueError("Coincident proposal required")
    edges = {e["id"]: e for e in case["edges"]}
    nodes = []
    for prefix, point in zip(("first", "second"), candidate["points_mm"]):
        edge = edges[candidate[prefix+"_edge"]]
        index = candidate[prefix+"_index"]
        if index not in (0, len(edge["centerline_mm"])-1):
            raise ValueError("Endpoint proposal required")
        if not np.array_equal(edge["centerline_mm"][index], point):
            raise ValueError("Endpoint changed")
        nodes.append(edge["start"] if index == 0 else edge["end"])
    with np.load(surface, allow_pickle=False) as data:
        mesh = trimesh.Trimesh(data["vertices"], data["faces"], process=False)
    points = np.asarray(candidate["points_mm"][:1])
    _, distance, _ = trimesh.proximity.closest_point(mesh, points)
    inside = bool(mesh.contains(points)[0])
    result = dict(status="PASS" if inside and distance[0] > 1e-6 else "UNKNOWN",
                  scope="Coincident point interior clearance only; graph nodes remain distinct",
                  union_sha256=links["union_sha256"], source_case_revision=revision,
                  source_node_ids=nodes, shared_original_node=nodes[0] == nodes[1],
                  coordinates_mm=points[0].tolist(), inside=inside,
                  distance_to_surface_mm=float(distance[0]), tolerance_mm=1e-6,
                  graph_edges_added=0, connection_status="UNADJUDICATED", live_scene_changed=False)
    (root / "access-coincident-link.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
