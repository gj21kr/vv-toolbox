"""Inspect every registered source path, without fitting it to the union."""
import hashlib
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.centerline_containment import inspect_centerline_containment


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--brachiocephalic", action="store_true")
    group.add_argument("--access-trunks", action="store_true")
    args = parser.parse_args()
    stem = ("femoral-anterior" if args.access_trunks else
            "anterior-brachiocephalic" if args.brachiocephalic else "anterior-core")
    evidence = Path("docs/evidence")
    parent = json.loads((evidence / f"{stem}-union.json").read_text())
    record = json.loads((evidence / "atlas-neck-volume-case.json").read_text())
    case, revision = load_case(record["derived_case_file"])
    path = Path("exports") / f"{stem}-union" / "candidate.npz"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if (parent["status"] != "CANDIDATE"
            or parent["lineage_check"]["status"] != "PASS"
            or revision != parent["source_case_revision"]
            or digest != parent["output_sha256"]):
        raise ValueError("Validated parent identity required")
    with np.load(path, allow_pickle=False) as data:
        mesh = trimesh.Trimesh(data["vertices"], data["faces"], process=False)
    names = parent["face_lineage"]["source_names"]
    metadata = case["inspection"]["atlas_scene_capture"]["estimated_metadata"]
    report = dict(source_case_revision=revision, union_sha256=digest,
                  source_names=names, status="RUNNING", rows=[],
                  scope="Every registered path of the union source parts; no fitted replacements",
                  anatomical_validation="NOT RUN", live_scene_changed=False)
    output = evidence / f"{stem}-paths.json"

    def save():
        temporary = output.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(output)

    save()
    for name in names:
        parts = [p for p in case["surface_parts"] if p["part_id"] == name]
        if len(parts) != 1 or not parts[0]["edge_ids"]:
            report["rows"].append(dict(part_id=name, status="UNKNOWN",
                                       reason="Unique source part and registered paths required"))
            save()
            continue
        ids = parts[0]["edge_ids"]
        declared = metadata.get(name, {}).get("centerline")
        for edge_id in ids:
            edges = [e for e in case["edges"] if e["id"] == edge_id]
            row = dict(part_id=name, edge_id=edge_id)
            if len(edges) != 1 or ids.count(edge_id) != 1:
                row.update(status="UNKNOWN", reason="Unique registered edge required")
            elif declared is not None and len(ids) != 1:
                row.update(status="UNKNOWN", reason="Declared estimate has ambiguous edge binding")
            else:
                points = np.asarray(declared if declared is not None
                                    else edges[0]["centerline_mm"], dtype="<f8")
                row.update(path_sha256=hashlib.sha256(points.tobytes()).hexdigest(),
                           provenance="declared-estimate" if declared is not None else "case-source-path")
                try:
                    row.update(inspect_centerline_containment(mesh, points))
                except ValueError as error:
                    row.update(status="UNKNOWN", reason=str(error))
            report["rows"].append(row)
            save()
            print(json.dumps(dict(part_id=name, edge_id=edge_id, status=row["status"],
                                  outside=len(row.get("outside_witnesses", [])),
                                  unresolved=len(row.get("unresolved_segments", [])))), flush=True)
    statuses = [r["status"] for r in report["rows"]]
    report["status"] = ("FAIL" if "FAIL" in statuses else
                        "UNKNOWN" if not statuses or "UNKNOWN" in statuses else "PASS")
    save()


if __name__ == "__main__":
    main()
