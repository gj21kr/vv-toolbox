"""Inspect synthetic link proposals for explicit access-trunk adjacencies."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.centerline_containment import inspect_centerline_containment
from vv_toolbox.path_link_candidates import enumerate_path_links


def main():
    root = Path("docs/evidence")
    read = lambda name: json.loads((root / name).read_text())
    parent = read("femoral-anterior-union.json")
    inspected = read("femoral-anterior-paths.json")
    case, revision = load_case(read("atlas-neck-volume-case.json")["derived_case_file"])
    path = Path("exports/femoral-anterior-union/candidate.npz")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if (parent["status"] != "CANDIDATE" or inspected["status"] != "PASS"
            or digest != parent["output_sha256"] or digest != inspected["union_sha256"]
            or revision != parent["source_case_revision"] or revision != inspected["source_case_revision"]):
        raise ValueError("Inspected source paths and surface required")
    with np.load(path, allow_pickle=False) as data:
        mesh = trimesh.Trimesh(data["vertices"], data["faces"], process=False)
    verified = {(r["part_id"], r["edge_id"]): r for r in inspected["rows"]}
    parts = {p["part_id"]: p for p in case["surface_parts"]}
    edges = {e["id"]: e for e in case["edges"]}
    metadata = case["inspection"]["atlas_scene_capture"]["estimated_metadata"]
    paths = {}
    for pid in parent["face_lineage"]["source_names"]:
        paths[pid] = {}
        for eid in parts[pid]["edge_ids"]:
            points = np.asarray(metadata.get(pid, {}).get("centerline", edges[eid]["centerline_mm"]), dtype="<f8")
            if hashlib.sha256(points.tobytes()).hexdigest() != verified[pid, eid]["path_sha256"]:
                raise ValueError("Inspected source path changed")
            paths[pid][eid] = points
    pairs = [("FJ2074", "FJ3466"), ("FJ3466", "FJ3464"), ("FJ3464", "FJ1932"),
             ("FJ2143", "FJ3567"), ("FJ3567", "FJ3565"), ("FJ3565", "FJ1932"),
             ("FJ1932", "FJ1931"), ("FJ1931", "FJ3411"),
             ("FJ3411", "FJ3483"), ("FJ3411", "FJ3417"),
             ("FJ3417", "FJ3564"), ("FJ3417", "FJ3579")]
    for cca, ica, suffix, side in (("FJ3483", "FJ1682M", "M", "left"),
                                    ("FJ3564", "FJ1682", "", "right")):
        neck = f"estimated_{side}_carotid_neck"
        pairs += [(cca, neck), (neck, ica), (ica, "FJ1654"+suffix),
                  (ica, "FJ1692"+suffix), ("FJ1654"+suffix, "FJ1655")]
    report = dict(status="RUNNING", source_case_revision=revision, union_sha256=digest,
                  scope="Every path pair for explicitly listed source adjacencies; sampled straight link proposals",
                  graph_edges_added=0, anatomical_connections="UNKNOWN", live_scene_changed=False, rows=[])
    output = root / "access-path-link-candidates.json"

    def save():
        temporary = output.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(output)

    save()
    for first, second in pairs:
        candidates = enumerate_path_links(paths[first], paths[second])
        for row in candidates:
            if row["distance_mm"] == 0:
                row["containment"] = dict(status="UNKNOWN", reason="Coincident samples require explicit node identity review")
            else:
                row["containment"] = inspect_centerline_containment(mesh, row["points_mm"])
        report["rows"].append(dict(first_part=first, second_part=second, candidates=candidates,
            contained_candidates=sum(r["containment"]["status"] == "PASS" for r in candidates)))
        save()
        print(json.dumps(dict(first=first, second=second, contained=report["rows"][-1]["contained_candidates"],
                              candidates=len(candidates))), flush=True)
    report["status"] = "PASS" if all(r["contained_candidates"] for r in report["rows"]) else "UNKNOWN"
    report["status_scope"] = "At least one contained proposal per declared adjacency; not graph route approval"
    save()


if __name__ == "__main__":
    main()
