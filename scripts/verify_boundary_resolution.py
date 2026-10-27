"""Check the complete boundary audit evidence, not anatomical correctness.

Run in the project Docker container after the ACA and MCA inspections.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reference-data/bodyparts3d"
INITIAL_DRAFT_SHA256 = "18daa39bbe0d5e86fe209c6dfb60af755e4276ca1ce2860d8108b69d82d63998"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    archive = SOURCE / "isa_BP3D_4.0_obj_99.zip"
    archive_sha = digest(archive)
    acquisition = json.loads((SOURCE / "acquisition.json").read_text())
    if archive_sha != acquisition["files"][archive.name]["sha256"]:
        raise ValueError("Archive differs from acquisition manifest")
    preview_sha = digest(SOURCE / "centerlines-preview.json")
    expected = {
        f"B.{side}.{artery}.{boundary}"
        for side in ("L", "R")
        for artery, boundaries in (
            ("ACA", ("A1_A2", "A2_A3", "A3_A4")),
            ("MCA", ("M1_M2", "M2_M3", "M3_M4")),
        )
        for boundary in boundaries
    }
    edges = {e["id"]: e for e in json.loads((SOURCE / "centerlines-preview.json").read_text())["edges"]}
    ids, reports, figures, candidates = [], [], [], []

    def verify_candidate(edge_id, candidate):
        points = np.asarray(edges[edge_id]["points"], dtype=float)
        index, fraction = candidate["interval_index"], candidate["fraction"]
        if not isinstance(index, int) or not 0 <= index < len(points)-1:
            raise ValueError("Invalid candidate interval")
        if not np.isfinite(fraction) or not 0 <= fraction <= 1:
            raise ValueError("Invalid candidate interpolation fraction")
        expected_point = points[index] + fraction * (points[index+1]-points[index])
        recorded_point = np.asarray(candidate["position_mm"], dtype=float)
        if recorded_point.shape != (3,) or not np.allclose(expected_point, recorded_point, atol=1e-8, rtol=0):
            raise ValueError("Candidate position differs from source edge interpolation")
        if "plane_normal" in candidate:
            normal = np.asarray(candidate["plane_normal"], dtype=float)
            if normal.shape != (3,) or not np.isclose(np.linalg.norm(normal), 1, atol=1e-8):
                raise ValueError("Invalid candidate plane normal")
        candidates.append({"edge_id": edge_id, "interval_index": index, "fraction": fraction})
    for name in ("aca-boundary-resolution", "mca-boundary-path-audit"):
        path = ROOT / f"docs/evidence/{name}.json"
        report = json.loads(path.read_text())
        if report["source_archive_sha256"] != archive_sha:
            raise ValueError(f"{name}: stale archive")
        recorded = report.get("centerline_preview_sha256", report.get("centerline_sha256"))
        if recorded != preview_sha:
            raise ValueError(f"{name}: stale centerlines")
        groups = report.get("boundaries", report.get("groups"))
        if not isinstance(groups, list) or len(groups) != 6:
            raise ValueError(f"{name}: expected six groups")
        for row in groups:
            ids.append(row["boundary_id"])
            if "position" not in row or row["position"] is not None:
                raise ValueError(f"{name}: audit must preserve unresolved approved positions")
            if row.get("candidate") is not None:
                verify_candidate(row["edge_id"], row["candidate"])
        for candidate in report.get("operational_candidates", []):
            verify_candidate(candidate["edge_id"], candidate)
        if name == "mca-boundary-path-audit":
            part_ids = [part["source_element_id"] for part in report["parts"]]
            recorded_edges = [edge["edge_id"] for part in report["parts"] for edge in part["edges"]]
            expected_edges = {e["id"] for e in edges.values() if e["part_id"] in part_ids}
            if len(part_ids) != 46 or len(set(part_ids)) != 46:
                raise ValueError("MCA source part coverage mismatch")
            if len(recorded_edges) != 120 or len(set(recorded_edges)) != 120 or set(recorded_edges) != expected_edges:
                raise ValueError("MCA source edge coverage mismatch")
            for part in report["parts"]:
                for edge in part["edges"]:
                    if edges[edge["edge_id"]]["part_id"] != part["source_element_id"]:
                        raise ValueError("MCA edge assigned to wrong source part")
        for figure in report["figures"]:
            target = (ROOT / figure["path"]).resolve()
            if not target.is_relative_to(ROOT.resolve()):
                raise ValueError("Figure path escapes workspace")
            if digest(target) != figure["sha256"]:
                raise ValueError(f"Figure changed: {figure['path']}")
            figures.append(figure["path"])
        reports.append({"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path)})
    if len(ids) != 12 or len(set(ids)) != 12 or set(ids) != expected:
        raise ValueError("Missing, duplicate or unexpected boundary group")
    if not figures:
        raise ValueError("No source inspection figures")
    draft_sha = digest(SOURCE / "cerebral-boundary-drafts.json")
    if draft_sha != INITIAL_DRAFT_SHA256:
        raise ValueError("App draft changed during the inspection; investigate before reporting preservation")
    regression_command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "tests/test_atlas_annotations.py", "tests/test_segment_materialization.py"]
    regression = subprocess.run(regression_command, cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, capture_output=True, text=True)
    if regression.returncode:
        raise RuntimeError(regression.stdout + regression.stderr)
    result = {
        "schema": "vv-toolbox.boundary-resolution-verification/1",
        "evidence_integrity": "PASS",
        "boundary_group_count": len(ids),
        "boundary_ids": sorted(ids),
        "source_archive_sha256": archive_sha,
        "centerline_preview_sha256": preview_sha,
        "app_draft_sha256": draft_sha,
        "app_draft_unchanged": True,
        "reports": reports,
        "verified_figure_count": len(figures),
        "verified_candidate_interpolations": candidates,
        "mca_source_coverage": {"parts": 46, "extraction_edges": 120},
        "annotation_regression": {"status": "PASS", "output": regression.stdout.strip(),
            "command": "PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_atlas_annotations.py tests/test_segment_materialization.py"},
        "anatomical_boundary_approval": "UNKNOWN",
        "limitation": "Hashes and group coverage do not prove anatomy or lumen continuity.",
    }
    output = ROOT / "docs/evidence/boundary-resolution-verification.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
