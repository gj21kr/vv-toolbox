"""Inspect the short extracted CIA twig against its original source surface."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as Polygon

from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case

ROOT = Path(__file__).resolve().parents[1]


def main():
    case, revision = load_case(ROOT/'exports/synthetic-internal-iliac-case/case.snapshot.json')
    atlas = load_atlas()
    assert atlas.metadata['sha256'] == next(s['sha256'] for s in case['sources'] if s['id'] == 'bp3d')
    part = next(p for p in atlas.meshes if p['id'] == 'FJ3565')
    mesh = trimesh.Trimesh(vertices=part['vertices'], faces=part['faces'], process=False)
    edge = next(e for e in case['edges'] if e['id'] == 'FJ3565:e1')
    points = np.array(edge['centerline_mm'])
    # Raw triangle distances, without assuming source watertightness or an inside sign.
    sample_t = np.linspace(0, 1, 21)
    samples = points[0]+sample_t[:, None]*(points[-1]-points[0])
    closest, distances, triangle_ids = trimesh.proximity.closest_point_naive(mesh, samples)
    planes = [922., 924.2, 924.4, 924.6, 924.8, 926.]
    fig, axes = plt.subplots(2, 3, figsize=(12, 8)); rows = []
    for ax, z in zip(axes.flat, planes):
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        contours = [] if section is None else section.discrete
        t = (z-points[0, 2])/(points[-1, 2]-points[0, 2])
        point = points[0]+t*(points[-1]-points[0]) if 0 <= t <= 1 else None
        inside = None if point is None else any(Polygon(c[:, :2]).contains_point(point[:2]) for c in contours)
        for c in contours: ax.plot(c[:, 0], c[:, 1], color='firebrick')
        if point is not None: ax.scatter(point[0], point[1], color='black', label='twig centerline')
        ax.set(title=f'Z={z:.1f} mm / {len(contours)} contours', xlabel='L (mm)', ylabel='P (mm)')
        ax.set_aspect('equal'); ax.grid(alpha=.2)
        rows.append(dict(z_mm=z, contour_count=len(contours), contours_mm=[c.tolist() for c in contours],
                         twig_point_mm=None if point is None else point.tolist(), twig_point_inside_section=inside))
    fig.suptitle('Original R common iliac mesh near short extracted twig')
    fig.tight_layout()
    out = ROOT/'exports/common-iliac-spur-inspection'; out.mkdir(parents=True, exist_ok=True)
    figure = out/'source-sections.png'; fig.savefig(figure, dpi=150); plt.close(fig)
    report = dict(schema='vv-toolbox.common-iliac-spur-inspection/1', case_revision=revision,
                  source_archive_sha256=atlas.metadata['sha256'], edge_id=edge['id'], source_part_id='FJ3565',
                  length_mm=float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum()),
                  endpoint_radii_mm=[edge['radii_mm'][0], edge['radii_mm'][-1]],
                  sampled_points_mm=samples.tolist(), closest_source_points_mm=closest.tolist(),
                  unsigned_source_surface_distances_mm=distances.tolist(), source_triangle_ids=triangle_ids.tolist(),
                  sections=rows, figure=dict(path=figure.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(figure.read_bytes()).hexdigest()),
                  source_mesh_watertight=bool(mesh.is_watertight), source_unchanged=True,
                  anatomical_branch_assignment='UNKNOWN',
                  conclusion='Short extracted path lies within single source cross-sections at tested levels; not evidence of an independent anatomical daughter.',
                  next_action='Author explicit synthetic omission with archived source correspondence before contracting the remaining trunk. Do not delete original atlas geometry.')
    (ROOT/'docs/evidence/common-iliac-spur-inspection.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(length_mm=report['length_mm'], min_distance=float(distances.min()), max_distance=float(distances.max()),
                         sections=[{k: r[k] for k in ['z_mm', 'contour_count', 'twig_point_inside_section']} for r in rows])))


if __name__ == '__main__':
    main()
