"""Measure all declared route transitions and inspect straight-link envelopes."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.centerline_containment import inspect_radius_envelope_containment
from vv_toolbox.route_junction_measurements import measure_route_junctions


def main():
    root = Path("docs/evidence")
    record = json.loads((root / "access-sample-graph.json").read_text())
    graph, revision = load_case(record["graph_file"])
    path = Path("exports/femoral-anterior-union/candidate.npz")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if revision != record["derived_revision"] or digest != record["surface_sha256"]:
        raise ValueError("Graph/surface inspection identity mismatch")
    with np.load(path, allow_pickle=False) as data:
        mesh = trimesh.Trimesh(data["vertices"], data["faces"], process=False)
    links = {r["edge_id"] for r in record["declarations"] if r["kind"] == "straight_link"}
    alias_nodes = {r["first"] for r in record["declarations"] if r["kind"] == "coincident_node_alias"}
    routes = []
    unique = {}
    for index, route in enumerate(record["routes"]):
        result = measure_route_junctions(graph, route)
        routes.append(dict(femoral_side=route["femoral_side"], carotid_side=route["carotid_side"],
                           target=route["target"], **result))
        for row in result["rows"]:
            if row["incoming_edge"] in links or row["outgoing_edge"] in links or row["node_id"] in alias_nodes:
                key = (row["node_id"], *sorted((row["incoming_edge"], row["outgoing_edge"])))
                unique.setdefault(key, dict(**row, route_indices=[]))["route_indices"].append(index)
    report = dict(status="RUNNING", graph_revision=revision, surface_sha256=digest,
                  route_measurements=routes, new_transitions=list(unique.values()), envelopes=[],
                  acceptance_limits="NOT SET", anatomical_validation="NOT RUN",
                  live_scene_changed=False, tube_wall_containment="NOT RUN")
    output = root / "access-graph-junctions.json"

    def save():
        temporary = output.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(output)

    save()
    print(json.dumps(dict(transitions=len(unique),
        maximum_turn_angle_deg=max(r["turn_angle_deg"] for r in unique.values()),
        maximum_radius_jump_mm=max(r["radius_jump_mm"] for r in unique.values()))), flush=True)
    edges = {e["id"]: e for e in graph["edges"]}
    for eid in sorted(links):
        edge = edges[eid]
        result = inspect_radius_envelope_containment(mesh, edge["centerline_mm"], edge["radii_mm"])
        report["envelopes"].append(dict(edge_id=eid, **result))
        save()
        print(json.dumps(dict(edge=eid, status=result["status"])), flush=True)
    report["status"] = "UNKNOWN"
    report["measurement_status"] = "PASS"
    report["envelope_status"] = ("FAIL" if any(r["status"] == "FAIL" for r in report["envelopes"])
                                  else "UNKNOWN" if any(r["status"] == "UNKNOWN" for r in report["envelopes"])
                                  else "PASS")
    report["scope"] = "Polyline transitions and radius-ball envelope only; envelope failure is not tube-wall exit proof"
    save()


if __name__ == "__main__":
    main()
