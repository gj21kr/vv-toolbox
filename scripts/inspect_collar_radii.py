"""Bind existing collar candidates to unchanged source radii and inspect envelopes."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.collar_link import build_radius_collar
from vv_toolbox.centerline_containment import inspect_radius_envelope_containment


def main():
    root = Path("docs/evidence")
    previous = json.loads((root / "access-collar-candidates.json").read_text())
    graph_record = json.loads((root / "access-sample-graph.json").read_text())
    graph, revision = load_case(graph_record["graph_file"])
    surface = Path("exports/femoral-anterior-union/candidate.npz")
    if revision != previous["graph_revision"] or hashlib.sha256(surface.read_bytes()).hexdigest() != previous["surface_sha256"]:
        raise ValueError("Source identity mismatch")
    edges = {e["id"]: e for e in graph["edges"]}
    paths, radii = [], []
    for binding in previous["oriented_source_bindings"]:
        edge = edges[binding["edge_id"]]
        points = np.asarray(edge["centerline_mm"], dtype=float)
        if hashlib.sha256(points.tobytes()).hexdigest() != binding["source_points_sha256"]:
            raise ValueError("Source path identity mismatch")
        radius = np.asarray(edge["radii_mm"], dtype=float)
        paths.append(points[::-1] if binding["reversed"] else points)
        radii.append(radius[::-1] if binding["reversed"] else radius)
    with np.load(surface, allow_pickle=False) as data:
        mesh = trimesh.Trimesh(data["vertices"], data["faces"], process=False)
    report = dict(status="RUNNING", graph_revision=revision,
                  surface_sha256=previous["surface_sha256"], rows=[],
                  graph_modified=False, live_scene_changed=False,
                  scope="Radius continuity and conservative ball envelope; not tube-wall acceptance")
    output = root / "access-collar-radii.json"
    for row in previous["candidates"]:
        artifact = Path(row["artifact"])
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != row["artifact_sha256"]:
            raise ValueError("Candidate identity mismatch")
        candidate = build_radius_collar(*paths, *radii, collar_mm=row["collar_mm"], samples=row["samples"])
        with np.load(artifact, allow_pickle=False) as data:
            if not np.array_equal(data["points_mm"], candidate["points_mm"]):
                raise ValueError("Candidate reconstruction mismatch")
        envelope = inspect_radius_envelope_containment(mesh, candidate["points_mm"], candidate["radii_mm"])
        target = artifact.with_name(artifact.stem + "-radius.npz")
        np.savez_compressed(target, points_mm=candidate["points_mm"], radii_mm=candidate["radii_mm"],
            incoming_points_mm=candidate["retained_incoming"]["points_mm"],
            incoming_radii_mm=candidate["retained_incoming"]["radii_mm"],
            outgoing_points_mm=candidate["retained_outgoing"]["points_mm"],
            outgoing_radii_mm=candidate["retained_outgoing"]["radii_mm"])
        report["rows"].append(dict(collar_mm=row["collar_mm"],
            endpoint_radii_mm=candidate["report"]["endpoint_radii_mm"],
            artifact=str(target), artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            envelope=envelope, radius_slope_continuity="NOT ENFORCED", branch_reattachment="NOT RUN"))
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(dict(collar_mm=row["collar_mm"], envelope=envelope["status"])), flush=True)
    report.update(status="UNKNOWN", inspection_status="COMPLETE")
    output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
