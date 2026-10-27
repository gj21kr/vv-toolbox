"""Generate separate carotid candidates; preserve the live atlas scene."""
import json
import argparse
from pathlib import Path

import numpy as np

from vv_toolbox.contour_bridge import bridge_contours
from vv_toolbox.mesh_self_contact import inspect_self_contact


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--preserve-corners',action='store_true')
    args=parser.parse_args()
    suffix='-corners' if args.preserve_corners else ''
    source = json.loads(Path("docs/evidence/neck-source-contours.json").read_text())
    groups = {}
    for row in source["rows"]:
        if "carotid" in row["part_id"] and row["plane_definition"] == "endpoint_tangent_normal":
            groups.setdefault(row["part_id"], {})[row["end"]] = row["profile"]
    folder = Path("exports/neck-contour-candidates"+suffix)
    folder.mkdir(parents=True, exist_ok=True)
    results = []
    for pid, profiles in sorted(groups.items()):
        mesh, report = bridge_contours(profiles[0], profiles[1],
                                      preserve_source_corners=args.preserve_corners)
        report["self_intersection"] = inspect_self_contact(mesh.vertices, mesh.faces)
        np.savez_compressed(folder / (pid + ".npz"), vertices=mesh.vertices, faces=mesh.faces)
        results.append(dict(part_id=pid, **report))
        print(pid, report["self_intersection"]["status"], flush=True)
    result = dict(case_revision=source["case_revision"], candidates=results,
                  live_scene_changed=False, source_geometry_changed=False)
    Path("docs/evidence/neck-contour-candidates"+suffix+".json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
