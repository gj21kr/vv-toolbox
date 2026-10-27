"""Build unaccepted noncircular walls with measured endpoint sections."""
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.profile_loft import loft_source_profiles
from vv_toolbox.mesh_self_contact import inspect_self_contact


def read_bound(row):
    path = Path(row["artifact"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != row["artifact_sha256"]:
        raise ValueError("Profile artifact identity mismatch")
    return json.loads(path.read_text())


def main():
    root = Path("docs/evidence")
    sections = json.loads((root / "access-collar-source-sections.json").read_text())
    attachments = json.loads((root / "access-collar-attachments.json").read_text())
    for key in ("graph_revision", "surface_sha256"):
        if sections[key] != attachments[key]:
            raise ValueError("Source identity mismatch")
    endpoints = {r["collar_mm"]: r for r in attachments["candidates"]}
    report = dict(status="RUNNING", graph_revision=sections["graph_revision"],
        surface_sha256=sections["surface_sha256"], rows=[], graph_modified=False,
        live_scene_changed=False, branch_preservation="NOT RUN")
    output = root / "access-collar-profile-lofts.json"
    for row in sections["rows"]:
        interior = read_bound(row)["profiles"]
        ends = read_bound(endpoints[row["collar_mm"]])["profiles"]
        profiles = copy.deepcopy([ends[0], *interior, ends[1]])
        for index, profile in enumerate(profiles):
            profile["index"] = index
        wall, metadata = loft_source_profiles(profiles, samples=64)
        target = Path("exports/access-collar-candidates") / f"collar-{row['collar_mm']}mm-profile-loft.npz"
        np.savez_compressed(target, vertices=wall.vertices, faces=wall.faces)
        entry = dict(collar_mm=row["collar_mm"], artifact=str(target),
            artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            vertices=len(wall.vertices), triangles=len(wall.faces),
            loft=metadata, self_contact="RUNNING",
            endpoint_policy="measured planes, perimeter resampling; original corners not guaranteed",
            surface_containment="NOT RUN")
        report["rows"].append(entry)
        output.write_text(json.dumps(report, indent=2)+"\n")
        entry["self_contact"] = inspect_self_contact(wall.vertices, wall.faces)
        output.write_text(json.dumps(report, indent=2)+"\n")
        print(json.dumps(dict(collar_mm=row["collar_mm"],
            self_contact=entry["self_contact"]["status"],
            contact_pairs=len(entry["self_contact"].get("contact_pairs", [])))), flush=True)
    report.update(status="UNKNOWN", inspection_status="COMPLETE")
    output.write_text(json.dumps(report, indent=2)+"\n")


if __name__ == "__main__":
    main()
