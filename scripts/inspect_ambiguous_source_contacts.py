"""Recheck named branch contacts on original inputs before any solid union."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.mesh_pair_contact import inspect_pair_contact


def main():
    root = Path("docs/evidence")
    record = json.loads((root / "atlas-neck-volume-case.json").read_text())
    context = json.loads((root / "anterior-core-context.json").read_text())
    case, revision = load_case(record["derived_case_file"])
    if revision != context["source_case_revision"]:
        raise ValueError("Source case identity mismatch")
    parts = {p["part_id"]: p for p in case["surface_parts"]}
    names = {p["id"]: p["name"] for p in load_atlas().metadata["parts"]}
    pairs = []
    for side in ("", "M"):
        for branch in ("FJ1662", "FJ1663"):
            for parent in ("FJ1682", "FJ1692"):
                pairs.append((branch + side, parent + side))
        pairs.append(("FJ1682" + side, "FJ1692" + side))
    pairs += [("FJ3564", "FJ3417"), ("FJ3564", "FJ3579"), ("FJ3417", "FJ3579")]
    meshes = {}
    source_hashes = {}
    for pid in sorted({pid for pair in pairs for pid in pair}):
        part = parts[pid]
        vertices = np.asarray(part["vertices_mm"], dtype="<f8")
        faces = np.asarray(part["faces"], dtype="<i8")
        meshes[pid] = vertices[faces]
        source_hashes[pid] = hashlib.sha256(vertices.tobytes() + faces.tobytes()).hexdigest()
    rows = []
    for first, second in pairs:
        result = inspect_pair_contact(meshes[first], meshes[second], tolerance_mm=1e-6)
        rows.append(dict(first=first, second=second, first_name=names[first],
                         second_name=names[second], **result))
        print(json.dumps(dict(first=first, second=second, status=result["status"],
                              pairs=len(result["contact_pairs"]))), flush=True)
    report = dict(source_case_revision=revision, source_geometry_sha256=source_hashes,
                  rows=rows, scope="Original source triangle intersections before union; not branch origin approval",
                  source_modified=False, anatomical_validation="NOT RUN", live_scene_changed=False)
    (root / "ambiguous-original-source-contacts.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
