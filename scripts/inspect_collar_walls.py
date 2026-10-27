"""Test actual sampled collar wall vertices against the fixed union."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.collar_surface import build_sampled_wall, inspect_wall_vertices


def main():
    root = Path("docs/evidence")
    source_path = root / "access-collar-radii.json"
    source = json.loads(source_path.read_text())
    surface = Path("exports/femoral-anterior-union/candidate.npz")
    if hashlib.sha256(surface.read_bytes()).hexdigest() != source["surface_sha256"]:
        raise ValueError("Surface identity mismatch")
    with np.load(surface, allow_pickle=False) as data:
        mesh = trimesh.Trimesh(data["vertices"], data["faces"], process=False)
    report = dict(status="RUNNING", source_report_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
        graph_revision=source["graph_revision"], surface_sha256=source["surface_sha256"],
        sides=32, rows=[], source_modified=False, live_scene_changed=False)
    output = root / "access-collar-walls.json"

    def save():
        temporary = output.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(output)

    save()
    for row in source["rows"]:
        artifact = Path(row["artifact"])
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != row["artifact_sha256"]:
            raise ValueError("Radius candidate identity mismatch")
        with np.load(artifact, allow_pickle=False) as data:
            wall = build_sampled_wall(data["points_mm"], data["radii_mm"], sides=report["sides"])
        target = artifact.with_name(artifact.stem + "-wall.npz")
        np.savez_compressed(target, vertices=wall.vertices, faces=wall.faces)
        result = inspect_wall_vertices(mesh, wall)
        report["rows"].append(dict(collar_mm=row["collar_mm"], artifact=str(target),
            artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest(), **result))
        save()
        print(json.dumps(dict(collar_mm=row["collar_mm"], status=result["status"],
                              outside_vertices=result["outside_count"])), flush=True)
    report["status"] = "FAIL" if any(r["status"] == "FAIL" for r in report["rows"]) else "UNKNOWN"
    report["inspection_status"] = "COMPLETE"
    save()


if __name__ == "__main__":
    main()
