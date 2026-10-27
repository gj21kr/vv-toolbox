"""Measure actual union contours along collar candidates without circularizing."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.source_sections import extract_source_sections


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
        surface_sha256=source["surface_sha256"], graph_revision=source["graph_revision"],
        rows=[], live_scene_changed=False, source_modified=False,
        scope="All non-endpoint stations; unique enclosing planar contours, not an accepted loft")
    output = root / "access-collar-source-sections.json"

    def save():
        temporary = output.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(output)

    save()
    for row in source["rows"]:
        artifact = Path(row["artifact"])
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != row["artifact_sha256"]:
            raise ValueError("Candidate identity mismatch")
        with np.load(artifact, allow_pickle=False) as data:
            points, radii = data["points_mm"], data["radii_mm"]
        sections = extract_source_sections(mesh, points)
        for profile in sections["profiles"]:
            radius = float(radii[profile["index"]])
            profile["stored_radius_mm"] = radius
            if profile["status"] == "MEASURED":
                profile["radius_minus_nearest_boundary_mm"] = radius-profile["center_boundary_distance_mm"]
                profile["center_to_contour_centroid_mm"] = float(np.linalg.norm(
                    np.asarray(profile["centroid_xyz_mm"])-points[profile["index"]]))
        target = artifact.with_name(artifact.stem + "-sections.json")
        target.write_text(json.dumps(sections, indent=2) + "\n")
        measured = [r for r in sections["profiles"] if r["status"] == "MEASURED"]
        report["rows"].append(dict(collar_mm=row["collar_mm"], counts=sections["counts"],
            artifact=str(target), artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            stored_circle_exceeds_nearest_boundary_count=sum(
                p["radius_minus_nearest_boundary_mm"] > 1e-6 for p in measured),
            maximum_centroid_offset_mm=max(
                (p["center_to_contour_centroid_mm"] for p in measured), default=None),
            endpoint_sections="NOT RUN", loft_surface="NOT RUN", branch_reattachment="NOT RUN"))
        save()
        print(json.dumps(report["rows"][-1]), flush=True)
    report.update(status="UNKNOWN", inspection_status="COMPLETE")
    save()


if __name__ == "__main__":
    main()
