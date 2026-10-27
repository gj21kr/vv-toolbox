"""Measure source contours at all declared neck endpoints, without modifying them."""
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.source_sections import extract_source_sections


def main():
    record = json.loads(Path("docs/evidence/atlas-neck-volume-case.json").read_text())
    case, revision = load_case(record["derived_case_file"])
    parts = {p["part_id"]: p for p in case["surface_parts"]}
    metadata = case["inspection"]["atlas_scene_capture"]["estimated_metadata"]
    rows = []
    for pid, info in sorted(metadata.items()):
        if info.get("kind") != "estimated-neck-connector":
            continue
        for end, target in enumerate(info["source_endpoint_ids"]):
            source = parts[target]
            mesh = trimesh.Trimesh(source["vertices_mm"], source["faces"], process=False)
            center = np.asarray(info["endpoint_centers"][end], dtype=float)
            axis = np.asarray(info["endpoint_axes"][end], dtype=float)
            axis /= np.linalg.norm(axis)
            # Keep both fixed definitions: the original horizontal measurement
            # and the plane normal to the declared connector endpoint tangent.
            for definition, normal in (("original_z_plane", np.array([0., 0., 1.])),
                                       ("endpoint_tangent_normal", axis)):
                path = np.array([center - normal, center, center + normal])
                profile = extract_source_sections(mesh, path)["profiles"][0]
                radius = float(info["endpoint_radii"][end])
                row = dict(part_id=pid, target=target, end=end,
                           plane_definition=definition, profile=profile,
                           connector_radius_mm=radius)
                if profile["status"] == "MEASURED":
                    row["circle_to_measured_area_ratio"] = (
                        np.pi * radius**2 / profile["area_mm2"])
                    row["circle_exceeds_nearest_boundary"] = (
                        radius > profile["center_boundary_distance_mm"] + 1e-8)
                rows.append(row)
    result = dict(schema="vv-toolbox.neck-source-contours/1",
                  case_revision=revision, rows=rows,
                  measured=sum(r["profile"]["status"] == "MEASURED" for r in rows),
                  unknown=sum(r["profile"]["status"] != "MEASURED" for r in rows),
                  geometry_changed=False, connected_lumen="NOT RUN",
                  anatomical_validation="NOT RUN",
                  scope="Source mesh section measurements at eight declared estimated neck ends")
    Path("docs/evidence/neck-source-contours.json").write_text(
        json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}))
    for row in rows:
        print(json.dumps({k: v for k, v in row.items() if k != "profile"} |
                         {"status": row["profile"]["status"]}))


if __name__ == "__main__":
    main()
