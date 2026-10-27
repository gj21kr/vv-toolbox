"""Keep all section contours around the largest measured loft deviations."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.source_sections import extract_source_sections


def main():
    root = Path("docs/evidence")
    deviation = json.loads((root / "access-collar-profile-deviation.json").read_text())
    radii = json.loads((root / "access-collar-radii.json").read_text())
    union = json.loads((root / "femoral-anterior-union.json").read_text())
    surface = Path("exports/femoral-anterior-union/candidate.npz")
    digest = hashlib.sha256(surface.read_bytes()).hexdigest()
    if digest != deviation["surface_sha256"] or digest != radii["surface_sha256"] or digest != union["output_sha256"]:
        raise ValueError("Source identity mismatch")
    with np.load(surface, allow_pickle=False) as data:
        mesh = trimesh.Trimesh(data["vertices"], data["faces"], process=False)
    report = dict(status="UNKNOWN", surface_sha256=digest, rows=[],
        scope="All contours in planes adjacent to maximum centroid deviation; not anatomical branch adjudication",
        source_modified=False, live_scene_changed=False)
    for row in deviation["rows"]:
        artifact = Path(row["artifact"])
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != row["artifact_sha256"]:
            raise ValueError("Deviation identity mismatch")
        with np.load(artifact, allow_pickle=False) as data:
            index = int(data["distances_mm"].argmax())
            face = int(data["source_face_ids"][index])
            distance = float(data["distances_mm"][index])
        source = next(r for r in radii["rows"] if r["collar_mm"] == row["collar_mm"])
        path = Path(source["artifact"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["artifact_sha256"]:
            raise ValueError("Curve identity mismatch")
        with np.load(path, allow_pickle=False) as data:
            points = data["points_mm"].copy()
        ring = index//128  # two triangles for each of 64 perimeter intervals
        profiles = []
        for station in (ring, ring+1):
            if not 0 < station < len(points)-1:
                raise ValueError("Maximum deviation touches endpoint; requires endpoint plane policy")
            profile = extract_source_sections(mesh, points[station-1:station+2],
                                              include_all_contours=True)["profiles"][0]
            profile["index"] = station
            profiles.append(profile)
        lineage = union["face_lineage"]
        owner = lineage["source_names"][lineage["face_source_indices"][face]]
        target = path.with_name(path.stem+"-branch-contours.json")
        target.write_text(json.dumps(dict(profiles=profiles), indent=2)+"\n")
        report["rows"].append(dict(collar_mm=row["collar_mm"], triangle_index=index,
            maximum_centroid_distance_mm=distance, source_face_index=face, nearest_source_owner=owner,
            stations=[p["index"] for p in profiles], areas_mm2=[p.get("area_mm2") for p in profiles],
            all_contour_counts=[len(p["all_contours"]) for p in profiles],
            artifact=str(target), artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            anatomical_identity="UNKNOWN", loft_replacement="NOT RUN"))
    (root / "access-collar-branch-contours.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
