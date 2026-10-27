"""Extend the synthetic anterior core at the right brachiocephalic junction."""
import hashlib
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.estimated_tube_volume import cap_estimated_neck
from vv_toolbox.solid_union import build_solid_union
from vv_toolbox.union_lineage import compose_face_lineage, verify_face_lineage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--access-trunks", action="store_true")
    args = parser.parse_args()
    parent_stem = "anterior-brachiocephalic" if args.access_trunks else "anterior-core"
    stem = "femoral-anterior" if args.access_trunks else "anterior-brachiocephalic"
    evidence = Path("docs/evidence")
    read = lambda name: json.loads((evidence / name).read_text())
    parent = read(f"{parent_stem}-union.json")
    case, revision = load_case(read("atlas-neck-volume-case.json")["derived_case_file"])
    path = Path("exports") / f"{parent_stem}-union" / "candidate.npz"
    if (revision != parent["source_case_revision"] or parent["status"] != "CANDIDATE"
            or parent["lineage_check"]["status"] != "PASS"
            or hashlib.sha256(path.read_bytes()).hexdigest() != parent["output_sha256"]):
        raise ValueError("Validated parent identity required")
    with np.load(path, allow_pickle=False) as data:
        mesh = trimesh.Trimesh(data["vertices"], data["faces"], process=False)
    parts = {p["part_id"]: p for p in case["surface_parts"]}
    added = (["FJ3411", "FJ1931", "FJ1932", "FJ3464", "FJ3466", "FJ2074",
              "FJ3565", "FJ3567", "FJ2143"] if args.access_trunks else ["FJ3417", "FJ3579"])
    sources = {}
    estimated_hashes = {}
    original = read("carotid-solid-union-diagnostic-float64-lineage.json")
    if original["source_case_revision"] != revision:
        raise ValueError("Original source case mismatch")
    for row in original["rows"]:
        estimated_hashes.update(row["input_surfaces"])
    for pid in parent["face_lineage"]["source_names"] + added:
        if pid.startswith("estimated_"):
            with np.load(Path("exports/neck-contour-candidates-corners") / (pid + ".npz"),
                         allow_pickle=False) as data:
                closed = cap_estimated_neck(dict(vertices=data["vertices"], faces=data["faces"],
                    metadata=dict(kind="estimated-neck-connector", original_atlas_geometry=False)),
                    max_planarity_mm=.001, cap_method="planar-earcut")
            source = trimesh.Trimesh(closed["vertices"], closed["faces"], process=False)
            digest = hashlib.sha256(np.asarray(source.vertices, dtype="<f8").tobytes()
                                    + np.asarray(source.faces, dtype="<i8").tobytes()).hexdigest()
            if digest != estimated_hashes[pid]["geometry_sha256"]:
                raise ValueError("Estimated source changed")
        else:
            part = parts[pid]
            source = trimesh.Trimesh(part["vertices_mm"], part["faces"], process=False)
        sources[pid] = source
    report = dict(source_case_revision=revision, parent_sha256=parent["output_sha256"],
                  added_sources=added, model_kind="synthetic",
                  reference_relation=dict(parent="FJ3417", daughters=["FJ3564", "FJ3579"],
                      source_url="https://doi.org/10.7759/cureus.9897",
                      specimen_status="unverified"),
                  whole_context="NOT RUN", centerline_containment="NOT RUN",
                  anatomical_segment_boundaries="UNKNOWN", live_scene_changed=False)
    if args.access_trunks:
        inventory = read("access-trunk-inputs.json")
        if inventory["source_case_revision"] != revision:
            raise ValueError("Access input case mismatch")
        hashes = {r["part_id"]: r["geometry_sha256"] for r in inventory["inputs"]}
        for pid in added:
            source = sources[pid]
            digest = hashlib.sha256(np.asarray(source.vertices, dtype="<f8").tobytes()
                                    + np.asarray(source.faces, dtype="<i8").tobytes()).hexdigest()
            if digest != hashes[pid]:
                raise ValueError("Access source changed")
        report["declared_access_inputs"] = dict(
            evidence_file="access-trunk-inputs.json", specimen_connections="UNKNOWN",
            excluded_alternative=["FJ3427"],
            reason="Thoracic and abdominal parts used explicitly; alternative descending-aorta part not added")
    try:
        parent_sources = {pid: sources[pid] for pid in parent["face_lineage"]["source_names"]}
        check = verify_face_lineage(mesh, parent_sources, parent["face_lineage"])
        if check["status"] != "PASS":
            raise ValueError("Parent source lineage changed")
        merged, audit = build_solid_union(dict(parent=mesh, **{pid: sources[pid] for pid in added}))
        flat = compose_face_lineage(audit["face_lineage"], {"parent": parent["face_lineage"]})
        check = verify_face_lineage(merged, sources, flat)
        if check["status"] != "PASS":
            raise ValueError("Original source lineage failed")
        folder = Path("exports") / f"{stem}-union"
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / "candidate.npz"
        np.savez_compressed(output, vertices=merged.vertices, faces=merged.faces)
        report.update(status="CANDIDATE", union=audit, face_lineage=flat, lineage_check=check,
                      output_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    except ValueError as error:
        report.update(status="FAIL", reason=str(error))
    (evidence / f"{stem}-union.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("union", "face_lineage", "lineage_check")}), flush=True)


if __name__ == "__main__":
    main()
