"""Source-preserving ACA boundary sensitivity inspection; execute inside Docker."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "exports/aca-boundary-followup"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def section(mesh, origin, normal):
    value = mesh.section(plane_origin=origin, plane_normal=normal)
    return [] if value is None else list(value.discrete)


def basis(normal):
    normal = normal / np.linalg.norm(normal)
    ref = np.eye(3)[np.argmin(np.abs(normal))]
    u = np.cross(normal, ref)
    u /= np.linalg.norm(u)
    return u, np.cross(normal, u)


def crossings(first, second):
    # Strict crossings only: tangencies/collinear contact are not asserted.
    count = 0
    for p in first:
        for q in second:
            for a, b in zip(p[:-1], p[1:]):
                for c, d in zip(q[:-1], q[1:]):
                    cross = lambda x, y: x[0]*y[1] - x[1]*y[0]
                    x = cross(b-a, c-a) * cross(b-a, d-a)
                    y = cross(d-c, a-c) * cross(d-c, b-c)
                    count += int(x < -1e-14 and y < -1e-14)
    return count


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    old_path = ROOT / "docs/evidence/aca-boundary-review.json"
    old_raw = old_path.read_bytes()
    old = json.loads(old_raw)
    source = ROOT / "reference-data/bodyparts3d"
    archive_raw = (source / "isa_BP3D_4.0_obj_99.zip").read_bytes()
    if sha(archive_raw) != old["source_archive_sha256"]:
        raise ValueError("Archive differs from prior inspection")
    cl_raw = (source / "centerlines-preview.json").read_bytes()
    if sha(cl_raw) != old["centerline_sha256"]:
        raise ValueError("Centerlines differ from prior inspection")
    edges = {e["id"]: e for e in json.loads(cl_raw)["edges"]}
    meshes = {}
    with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
        for ident, expected in old["obj_sha256"].items():
            names = [n for n in archive.namelist() if Path(n).name == ident + ".obj"]
            if len(names) != 1:
                raise ValueError("Non-unique source OBJ")
            raw = archive.read(names[0])
            if sha(raw) != expected:
                raise ValueError("OBJ differs from prior inspection")
            meshes[ident] = trimesh.load(io.BytesIO(raw), file_type="obj", process=False)
    results = []
    fig, axes = plt.subplots(4, 3, figsize=(12, 15))
    row = 0
    for boundary in old["boundaries"]:
        if boundary.get("localization_scope") != "region_only":
            continue
        samples = boundary["centerline_samples"]
        edge_ids = {s["edge_id"] for s in samples}
        if len(edge_ids) != 1:
            raise ValueError("Region spans multiple edges; do not invent a path")
        edge_id = next(iter(edge_ids))
        indices = sorted(s["point_index"] for s in samples)
        if indices != list(range(indices[0], indices[-1]+1)):
            raise ValueError("Non-contiguous region")
        points = np.asarray(edges[edge_id]["points"], dtype=float)
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        start, end = arc[indices[0]], arc[indices[-1]]
        candidates = []
        for col, fraction in enumerate([0.0, 0.5, 1.0]):
            station = start + fraction * (end-start)
            index = min(int(np.searchsorted(arc, station, side="right")-1), len(points)-2)
            ratio = (station-arc[index])/(arc[index+1]-arc[index])
            origin = points[index]*(1-ratio) + points[index+1]*ratio
            # A local 2 mm chord reduces one-voxel directional stepping. This is
            # a declared inspection convention, not an anatomical definition.
            tangent = np.array([np.interp(min(arc[-1], station+1), arc, points[:, j]) -
                                np.interp(max(0, station-1), arc, points[:, j]) for j in range(3)])
            tangent /= np.linalg.norm(tangent)
            u, v = basis(tangent)
            loops = section(meshes[edges[edge_id]["part_id"]], origin, tangent)
            records = []
            ax = axes[row, col]
            for loop in loops:
                xy = np.c_[(loop-origin) @ u, (loop-origin) @ v]
                closed = bool(np.linalg.norm(loop[0]-loop[-1]) < 1e-6)
                area = abs(float(np.sum(xy[:-1, 0]*xy[1:, 1]-xy[1:, 0]*xy[:-1, 1])/2)) if closed else None
                records.append({"closed": closed, "area_mm2": area,
                                "perimeter_mm": float(np.linalg.norm(np.diff(loop, axis=0), axis=1).sum()),
                                "center_distance_mm": float(np.linalg.norm(xy.mean(axis=0))),
                                "points_mm": loop.tolist()})
                ax.plot(xy[:, 0], xy[:, 1], color="firebrick")
            ax.scatter([0], [0], marker="+", color="black")
            ax.set(xlim=(-4, 4), ylim=(-4, 4), xlabel="plane U (mm)", ylabel="plane V (mm)")
            ax.set_aspect("equal")
            ax.grid(alpha=.3)
            ax.set_title(f'{boundary["boundary_id"]}\nregion {fraction:.0%}; s={station:.2f} mm')
            candidates.append({"evidence_status": "operational_candidate", "region_fraction": fraction, "station_from_edge_start_mm": float(station),
                               "edge_point_interval": [index, index+1], "interval_fraction": float(ratio),
                               "position_mm": origin.tolist(), "plane_normal": tangent.tolist(),
                               "section_contours": records, "approved": False})
        results.append({"boundary_id": boundary["boundary_id"], "status": "region_only",
                        "edge_id": edge_id, "region_arclength_mm": float(end-start),
                        "half_window_station_sensitivity_mm": float((end-start)/2),
                        "candidate_rule": "start / arc midpoint / end of previously reviewed contiguous region; 2 mm tangent chord",
                        "candidates": candidates, "exact_boundary_approved": False})
        row += 1
    fig.suptitle("Local +/-4 mm section windows; all contours, including remote vessel recrossings, retained in JSON")
    fig.tight_layout(rect=[0, 0, 1, .98])
    fig.savefig(OUT / "aca-operational-plane-sensitivity.png", dpi=150)
    plt.close(fig)
    levels = np.arange(1536.5, 1539.0001, .25)
    fig, axes = plt.subplots(3, 4, figsize=(16, 12))
    sweep = []
    for ax, level in zip(axes.flat, levels):
        curves = {ident: section(meshes[ident], [0, 0, level], [0, 0, 1])
                  for ident in ["FJ1654", "FJ1654M", "FJ1655"]}
        item = {"z_mm": float(level), "strict_contour_crossings": {}, "contour_counts": {k: len(v) for k, v in curves.items()}}
        for side, ident, color in [("R", "FJ1654", "firebrick"), ("L", "FJ1654M", "darkorange"), ("ACom", "FJ1655", "royalblue")]:
            for curve in curves[ident]:
                ax.plot(curve[:, 0], curve[:, 1], color=color)
            if side != "ACom":
                item["strict_contour_crossings"][side] = crossings([c[:, :2] for c in curves[ident]], [c[:, :2] for c in curves["FJ1655"]])
        sweep.append(item)
        ax.set(xlim=(-7, 7), ylim=(-118, -107), xlabel="X (mm)", ylabel="Y (mm)")
        ax.set_aspect("equal")
        ax.grid(alpha=.3)
        ax.set_title(f'Z={level:.2f}; crossings R/L={item["strict_contour_crossings"]["R"]}/{item["strict_contour_crossings"]["L"]}')
    axes.flat[-1].axis("off")
    fig.suptitle("Native source axial sections: R ACA red; L ACA orange; ACom blue. Crossing is not an open lumen.")
    fig.tight_layout()
    fig.savefig(OUT / "acom-quarter-mm-sections.png", dpi=150)
    plt.close(fig)
    for side in ["R", "L"]:
        hit = [x["z_mm"] for x in sweep if x["strict_contour_crossings"][side] > 0]
        results.append({"boundary_id": f"B.{side}.ACA.A1_A2", "status": "candidate",
                        "strict_crossing_sample_levels_z_mm": hit,
                        "sampled_crossing_span_mm": [min(hit), max(hit)] if hit else None,
                        "exact_boundary_approved": False,
                        "interpretation": "Sampled contour crossings establish intersecting separate surfaces, not a shared ostial plane or lumen continuity. Bounds are sampled levels, not exact intersection extrema."})
    report = {"schema": "vv_toolbox.aca_boundary_followup/1", "review_date": "2026-10-20",
              "coordinate_frame_id": old["coordinate_frame_id"], "units": "mm",
              "source_archive_sha256": sha(archive_raw), "centerline_sha256": sha(cl_raw),
              "previous_report_sha256": sha(old_raw), "obj_sha256": old["obj_sha256"],
              "boundaries": results, "acom_axial_sweep": sweep,
              "summary": {"boundaries_rechecked": 6, "operational_plane_candidates": 12,
                          "region_only": 4, "attachment_candidate": 2, "approved_exact_boundaries": 0},
              "limitations": ["No source geometry or annotations were changed.",
                              "Operational candidates are inspection conventions, not clinically validated boundaries.",
                              "Section loop areas are individual contour areas, not certified lumen areas; holes and off-target loops are retained separately.",
                              "No expert interobserver or patient validation; no lumen union performed."],
              "figures": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p.read_bytes())} for p in sorted(OUT.glob("*.png"))]}
    path = ROOT / "docs/evidence/aca-boundary-followup.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "regions": [{"id": r["boundary_id"], "length_mm": r.get("region_arclength_mm"), "crossing_z": r.get("sampled_crossing_span_mm")} for r in results]}))


if __name__ == "__main__":
    main()
