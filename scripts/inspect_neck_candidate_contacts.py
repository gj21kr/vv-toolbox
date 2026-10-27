"""Screen carotid candidates against original and estimated vascular surfaces."""
import hashlib
import argparse
import json
from pathlib import Path

import numpy as np

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_neck import build_neck_repairs
from vv_toolbox.mesh_pair_contact import inspect_pair_contact


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--preserve-corners',action='store_true')
    args=parser.parse_args()
    suffix='-corners' if args.preserve_corners else ''
    atlas = load_atlas()
    estimated, _ = build_neck_repairs(atlas)
    parts = {p["id"]: p for p in [*atlas.meshes, *estimated]
             if p["layer"] in ("arterial", "systemic_venous", "hepatic_portal")}
    measurements = json.loads(Path("docs/evidence/neck-source-contours.json").read_text())
    targets = {}
    for row in measurements["rows"]:
        targets.setdefault(row["part_id"], set()).add(row["target"])
    candidates = {}
    hashes = {}
    for pid in sorted(targets):
        if "carotid" not in pid:
            continue
        path = Path("exports/neck-contour-candidates"+suffix) / (pid + ".npz")
        hashes[pid] = hashlib.sha256(path.read_bytes()).hexdigest()
        with np.load(path, allow_pickle=False) as data:
            candidates[pid] = dict(id=pid, vertices=data["vertices"].copy(),
                                   faces=data["faces"].copy(), layer="arterial")
    # Both candidates coexist: do not test a new left against an obsolete right.
    parts.update(candidates)
    rows = []
    for pid, candidate in candidates.items():
        vertices = candidate["vertices"]
        low, high = vertices.min(0), vertices.max(0)
        for other_id, other in sorted(parts.items()):
            if other_id == pid:
                continue
            ov = np.asarray(other["vertices"])
            row = dict(part_id=pid, other_id=other_id, layer=other["layer"],
                       declared_attachment=other_id in targets[pid])
            if np.any(ov.min(0) > high + 1e-8) or np.any(ov.max(0) < low - 1e-8):
                row.update(status="AABB_SEPARATED", contact_count=0)
            else:
                contact = inspect_pair_contact(
                    vertices[candidate["faces"]], ov[np.asarray(other["faces"])])
                row.update(status=contact["status"], complete=contact["complete"],
                           contact_count=len(contact["contact_pairs"]),
                           checked_pairs=contact["checked_pairs"],
                           contact_pairs=contact["contact_pairs"])
            rows.append(row)
        print(pid, "screened", len(parts)-1, "neighbors", flush=True)
    unexpected = [r for r in rows if not r["declared_attachment"]
                  and r["status"] not in ("AABB_SEPARATED", "NO_SURFACE_CONTACT_DETECTED")]
    result = dict(schema="vv-toolbox.neck-candidate-contact/1",
                  candidate_file_sha256=hashes, neighbor_parts=len(parts),
                  rows=rows, unexpected_contact_or_unknown=len(unexpected),
                  status="CONTACT_OR_UNKNOWN" if unexpected else "NO_UNEXPECTED_SURFACE_CONTACT",
                  containment="NOT RUN", source_union="NOT RUN",
                  anatomical_validation="NOT RUN", live_scene_changed=False)
    Path("docs/evidence/neck-candidate-contacts"+suffix+".json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}))
    print(json.dumps([{k: v for k, v in r.items() if k != "contact_pairs"} for r in unexpected]))


if __name__ == "__main__":
    main()
