"""Inspect fixed collar candidates without changing the source graph or scene."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.collar_link import build_collar_link
from vv_toolbox.centerline_containment import inspect_centerline_containment


def main():
    evidence = Path("docs/evidence")
    record = json.loads((evidence / "access-sample-graph.json").read_text())
    graph, revision = load_case(record["graph_file"])
    surface = Path("exports/femoral-anterior-union/candidate.npz")
    digest = hashlib.sha256(surface.read_bytes()).hexdigest()
    if revision != record["derived_revision"] or digest != record["surface_sha256"]:
        raise ValueError("Graph/surface identity mismatch")
    route = next(r for r in record["routes"] if "declared-link:10" in r["edges"])
    position = route["edges"].index("declared-link:10")
    edges = {e["id"]: e for e in graph["edges"]}
    bindings, paths = [], []
    for index in (position-1, position+1):
        edge = edges[route["edges"][index]]
        endpoints = tuple(route["nodes"][index:index+2])
        if endpoints == (edge["start"], edge["end"]):
            reverse = False
        elif endpoints == (edge["end"], edge["start"]):
            reverse = True
        else:
            raise ValueError("Invalid route incidence")
        points = np.asarray(edge["centerline_mm"], dtype=float)
        paths.append(points[::-1].copy() if reverse else points.copy())
        bindings.append(dict(edge_id=edge["id"], reversed=reverse,
            source_points_sha256=hashlib.sha256(points.tobytes()).hexdigest()))
    with np.load(surface, allow_pickle=False) as data:
        mesh = trimesh.Trimesh(data["vertices"], data["faces"], process=False)
    output = Path("exports/access-collar-candidates")
    output.mkdir(parents=True, exist_ok=True)
    report = dict(status="RUNNING", graph_revision=revision, surface_sha256=digest,
        replaced_link="declared-link:10", oriented_source_bindings=bindings,
        fixed_collars_mm=[5, 10, 20], samples=129, candidates=[],
        graph_modified=False, live_scene_changed=False,
        scope="Sampled collar curves only; retained branches, radius and continuous cubic not approved")
    report_path = evidence / "access-collar-candidates.json"

    def save():
        temporary = report_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(report_path)

    save()
    for collar in report["fixed_collars_mm"]:
        try:
            candidate = build_collar_link(*paths, collar_mm=collar, samples=report["samples"])
        except ValueError as error:
            report["candidates"].append(dict(collar_mm=collar, construction="FAIL", reason=str(error)))
            save()
            continue
        artifact = output / f"collar-{collar}mm.npz"
        np.savez_compressed(artifact, points_mm=candidate["points_mm"],
                            controls_mm=candidate["controls_mm"])
        row = dict(**candidate["report"], artifact=str(artifact),
                   artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest())
        report["candidates"].append(row)
        save()
        containment = inspect_centerline_containment(mesh, candidate["points_mm"])
        row.update(surface_containment=containment["status"], containment=containment)
        save()
        print(json.dumps(dict(collar_mm=collar, containment=containment["status"],
            start_angle=row["sampled_start_angle_deg"], end_angle=row["sampled_end_angle_deg"])), flush=True)
    report["status"] = "UNKNOWN"
    report["inspection_status"] = "COMPLETE"
    save()


if __name__ == "__main__":
    main()
