"""Measure endpoint contours and inventory branches requiring explicit reattachment."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.source_sections import extract_source_sections


def main():
    root = Path("docs/evidence")
    source_path = root / "access-collar-candidates.json"
    source = json.loads(source_path.read_text())
    graph_record = json.loads((root / "access-sample-graph.json").read_text())
    graph, revision = load_case(graph_record["graph_file"])
    surface = Path("exports/femoral-anterior-union/candidate.npz")
    if revision != source["graph_revision"] or hashlib.sha256(surface.read_bytes()).hexdigest() != source["surface_sha256"]:
        raise ValueError("Source identity mismatch")
    with np.load(surface, allow_pickle=False) as data:
        mesh = trimesh.Trimesh(data["vertices"], data["faces"], process=False)
    edges = {e["id"]: e for e in graph["edges"]}
    selected = {r["edge_id"] for r in source["oriented_source_bindings"]} | {source["replaced_link"]}
    bindings = []
    for side, binding in zip(("incoming", "outgoing"), source["oriented_source_bindings"]):
        edge = edges[binding["edge_id"]]
        points = np.asarray(edge["centerline_mm"], dtype=float)
        if hashlib.sha256(points.tobytes()).hexdigest() != binding["source_points_sha256"]:
            raise ValueError("Path identity mismatch")
        oriented = points[::-1] if binding["reversed"] else points
        first, last = (edge["end"], edge["start"]) if binding["reversed"] else (edge["start"], edge["end"])
        old_node = last if side == "incoming" else first
        incident = [e["id"] for e in graph["edges"] if old_node in (e["start"], e["end"])]
        bindings.append(dict(side=side, edge_id=edge["id"], old_attachment_node=old_node,
            incident_edges=incident, other_edges_requiring_reattachment=sorted(set(incident)-selected),
            oriented=oriented))
    report = dict(status="UNKNOWN", graph_revision=revision, surface_sha256=source["surface_sha256"],
        graph_modified=False, live_scene_changed=False,
        branch_inventory=[{k: v for k, v in b.items() if k != "oriented"} for b in bindings],
        candidates=[], scope="Endpoint plane sections and graph incidences; no branch relocation")
    for candidate in source["candidates"]:
        artifact = Path(candidate["artifact"])
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != candidate["artifact_sha256"]:
            raise ValueError("Candidate identity mismatch")
        with np.load(artifact, allow_pickle=False) as data:
            curve = data["points_mm"].copy()
        endpoints = []
        for i, binding in enumerate(bindings):
            index = candidate[binding["side"]+"_anchor"]["interval_index"]
            tangent = np.diff(binding["oriented"], axis=0)[index]
            tangent /= np.linalg.norm(tangent)
            point = curve[0 if i == 0 else -1]
            # Symmetric probes define the exact retained-side tangent plane.
            profile = extract_source_sections(mesh, [point-tangent, point, point+tangent])["profiles"][0]
            profile["side"] = binding["side"]
            endpoints.append(profile)
        target = artifact.with_name(artifact.stem+"-attachments.json")
        target.write_text(json.dumps(dict(profiles=endpoints), indent=2)+"\n")
        report["candidates"].append(dict(collar_mm=candidate["collar_mm"],
            artifact=str(target), artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            endpoint_statuses=[p["status"] for p in endpoints],
            endpoint_areas_mm2=[p.get("area_mm2") for p in endpoints],
            branch_preservation="NOT RUN", contour_correspondence="NOT RUN"))
    report["inspection_status"] = "COMPLETE"
    (root / "access-collar-attachments.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
