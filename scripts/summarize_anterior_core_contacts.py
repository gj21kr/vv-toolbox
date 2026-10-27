"""Map contact evidence to original source owners; never approve junctions."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.atlas import load_atlas


def main():
    root = Path("docs/evidence")
    parent = json.loads((root / "anterior-core-union.json").read_text())
    context_path = root / "anterior-core-context.json"
    context = json.loads(context_path.read_text())
    path = Path("exports/anterior-core-union/candidate.npz")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if (digest != parent["output_sha256"] or digest != context["candidate_sha256"]
            or parent["source_case_revision"] != context["source_case_revision"]):
        raise ValueError("Contact evidence and candidate identity mismatch")
    lineage = parent["face_lineage"]
    with np.load(path, allow_pickle=False) as data:
        triangles = data["vertices"][data["faces"]]
    owners = np.asarray(lineage["face_source_indices"])
    if len(owners) != len(triangles):
        raise ValueError("Complete per-face ownership required")
    metadata = {p["id"]: p for p in load_atlas().metadata["parts"]}
    rows = []
    for pair in context["rows"]:
        if pair["status"] == "SEPARATED":
            continue
        pid = pair["neighbor_id"]
        contacts = np.asarray(pair["contact_pairs"], dtype=int)
        ids = np.unique(contacts[:, 0]) if contacts.size else np.array([], dtype=int)
        if len(ids) and (ids.min() < 0 or ids.max() >= len(triangles)):
            raise ValueError("Contact face outside candidate")
        counts = {name: int(np.count_nonzero(owners[ids] == i))
                  for i, name in enumerate(lineage["source_names"])
                  if np.any(owners[ids] == i)}
        bounds = (np.stack((triangles[ids].min(axis=(0, 1)),
                            triangles[ids].max(axis=(0, 1)))).tolist()
                  if len(ids) else None)
        rows.append(dict(neighbor_id=pid, neighbor_name=metadata.get(pid, {}).get("name", pid),
                         status=pair["status"], complete=pair["complete"],
                         contact_pair_count=len(contacts),
                         candidate_face_count=len(ids), source_face_counts=counts,
                         contacting_candidate_triangle_bounds_mm=bounds,
                         containment=pair.get("containment"),
                         junction_approval="UNKNOWN"))
    report = dict(candidate_sha256=digest,
                  context_file_sha256=hashlib.sha256(context_path.read_bytes()).hexdigest(),
                  source_case_revision=parent["source_case_revision"],
                  context_status=context["status"], inspected_neighbors=context["neighbor_count"],
                  rows=rows, scope="Source ownership and bounds of contacting triangles, not exact intersection loci",
                  anatomical_validation="NOT RUN", live_scene_changed=False)
    (root / "anterior-core-contact-locations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(neighbors=len(rows), source_owners=sorted(
        {name for row in rows for name in row["source_face_counts"]}))), flush=True)


if __name__ == "__main__":
    main()
