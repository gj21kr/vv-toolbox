"""Inventory original access trunks and all pairwise surface contacts."""
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.mesh_pair_contact import inspect_pair_contact
from vv_toolbox.surface_indexing import exact_vertex_index_copy


def main():
    evidence = Path("docs/evidence")
    record = json.loads((evidence / "atlas-neck-volume-case.json").read_text())
    case, revision = load_case(record["derived_case_file"])
    # Include the separately named descending-aorta parts, without assuming
    # which ones continue or overlap. The pair inventory answers that first.
    ids = ("FJ3411", "FJ3427", "FJ1931", "FJ1932", "FJ3464", "FJ3466",
           "FJ2074", "FJ3565", "FJ3567", "FJ2143", "FJ3417", "FJ3564", "FJ3483")
    parts = {p["part_id"]: p for p in case["surface_parts"]}
    names = {p["id"]: p["name"] for p in load_atlas().metadata["parts"]}
    report = dict(source_case_revision=revision, status="RUNNING", inputs=[], pairs=[],
                  scope="13 named access trunks; all unordered original surface pairs",
                  graph_connections="NOT APPROVED", self_contact="NOT RUN",
                  containment="NOT RUN", source_modified=False, live_scene_changed=False)
    meshes = {}
    output = evidence / "access-trunk-inputs.json"

    def save():
        temporary = output.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(output)

    for pid in ids:
        part = parts[pid]
        vertices = np.asarray(part["vertices_mm"], dtype="<f8")
        faces = np.asarray(part["faces"], dtype="<i8")
        source = trimesh.Trimesh(vertices, faces, process=False)
        normalized, indexing = exact_vertex_index_copy(source)
        meshes[pid] = source.triangles
        report["inputs"].append(dict(part_id=pid, name=names[pid], indexing=indexing,
            is_volume=bool(normalized.is_volume),
            geometry_sha256=hashlib.sha256(vertices.tobytes() + faces.tobytes()).hexdigest()))
    save()
    for first, second in itertools.combinations(ids, 2):
        result = inspect_pair_contact(meshes[first], meshes[second], tolerance_mm=1e-6)
        report["pairs"].append(dict(first=first, second=second, **result))
        save()
        if result["contact_pairs"] or not result["complete"]:
            print(json.dumps(dict(first=first, second=second, status=result["status"],
                                  pairs=len(result["contact_pairs"]))), flush=True)
    report["status"] = "PASS" if all(p["complete"] for p in report["pairs"]) else "UNKNOWN"
    report["status_scope"] = "Pair inspection completeness only, not geometry acceptance"
    save()
    print(json.dumps(dict(status=report["status"], inspected_pairs=len(report["pairs"]))), flush=True)


if __name__ == "__main__":
    main()
