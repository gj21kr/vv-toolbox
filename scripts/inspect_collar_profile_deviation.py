"""Measure every candidate triangle centroid against the unchanged union surface."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.route_junction_measurements import measure_route_junctions


def main():
    root = Path("docs/evidence")
    lofts = json.loads((root / "access-collar-profile-lofts.json").read_text())
    graphs = json.loads((root / "access-collar-graphs.json").read_text())
    if graphs["parent_revision"] != lofts["graph_revision"]:
        raise ValueError("Graph/loft parent mismatch")
    surface = Path("exports/femoral-anterior-union/candidate.npz")
    if hashlib.sha256(surface.read_bytes()).hexdigest() != lofts["surface_sha256"]:
        raise ValueError("Surface hash mismatch")
    with np.load(surface, allow_pickle=False) as data:
        mesh = trimesh.Trimesh(data["vertices"], data["faces"], process=False)
    report = dict(status="RUNNING", surface_sha256=lofts["surface_sha256"], rows=[],
        scope="All triangle centroids, one-way nearest-surface distances; not Hausdorff bounds",
        acceptance_limits="NOT SET", source_modified=False, live_scene_changed=False)
    output = root / "access-collar-profile-deviation.json"

    def save():
        temporary = output.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, indent=2)+"\n")
        temporary.replace(output)

    for item in graphs["rows"]:
        graph, revision = load_case(item["graph_file"])
        if revision != item["revision"]:
            raise ValueError("Derived graph mismatch")
        transitions = {}
        for route in item["routes"]:
            for row in measure_route_junctions(graph, route)["rows"]:
                if row["node_id"] in graph["collar_graph"]["anchors"]:
                    transitions[row["node_id"]] = row
        loft = next(r for r in lofts["rows"] if r["collar_mm"] == item["collar_mm"])
        path = Path(loft["artifact"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != loft["artifact_sha256"]:
            raise ValueError("Loft hash mismatch")
        with np.load(path, allow_pickle=False) as data:
            triangles = data["vertices"][data["faces"]]
        query = triangles.mean(axis=1)
        entry = dict(collar_mm=item["collar_mm"], graph_revision=revision,
            loft_sha256=loft["artifact_sha256"], transitions=list(transitions.values()),
            total_centroids=len(query), inspected_centroids=0, status="RUNNING")
        report["rows"].append(entry)
        save()
        distances, face_ids = [], []
        for start in range(0, len(query), 128):
            _, distance, faces = trimesh.proximity.closest_point(mesh, query[start:start+128])
            if not np.isfinite(distance).all():
                raise ValueError("Nonfinite surface distance")
            distances.extend(distance.tolist())
            face_ids.extend(faces.tolist())
            entry["inspected_centroids"] = len(distances)
            if start % 2048 == 0:
                save()
        values = np.asarray(distances)
        target = path.with_name(path.stem+"-deviation.npz")
        np.savez_compressed(target, distances_mm=values, source_face_ids=np.asarray(face_ids),
                            centroids_mm=query)
        entry.update(status="MEASURED", maximum_distance_mm=float(values.max()),
            mean_distance_mm=float(values.mean()), p95_distance_mm=float(np.percentile(values, 95)),
            artifact=str(target), artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            continuous_surface_distance="NOT RUN", bidirectional_distance="NOT RUN")
        save()
        print(json.dumps(dict(collar_mm=item["collar_mm"], maximum_distance_mm=entry["maximum_distance_mm"],
                              p95_distance_mm=entry["p95_distance_mm"])), flush=True)
    report.update(status="UNKNOWN", inspection_status="COMPLETE")
    save()


if __name__ == "__main__":
    main()
