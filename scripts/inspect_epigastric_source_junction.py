"""Compare original external iliac / epigastric sections with synthetic surface."""
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
from inspect_brachiocephalic_junction import crossings

ROOT = Path(__file__).resolve().parents[1]


def main():
    case, revision = load_case(ROOT/'exports/synthetic-iliofemoral-case/case.snapshot.json')
    atlas = load_atlas()
    assert atlas.metadata['sha256'] == next(s['sha256'] for s in case['sources'] if s['id'] == 'bp3d')
    parts = {m['id']: m for m in atlas.meshes if m['id'] in {'FJ3567', 'FJ3604'}}
    meshes = {pid: trimesh.Trimesh(vertices=p['vertices'], faces=p['faces'], process=False) for pid, p in parts.items()}
    inspection_path = ROOT/'docs/evidence/iliofemoral-candidate-inspection.json'
    inspection = json.loads(inspection_path.read_text())
    assert inspection['candidate_revision'] == revision
    surface = next(s for s in inspection['surfaces'] if s['side'] == 'R')
    surface_path = ROOT/surface['path']
    assert hashlib.sha256(surface_path.read_bytes()).hexdigest() == surface['sha256']
    with np.load(surface_path) as data:
        meshes['candidate'] = trimesh.Trimesh(vertices=data['vertices_mm'], faces=data['faces'], process=False)
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    rows = []
    for ax, z in zip(axes.flat, [826., 829., 832., 835., 838., 841.]):
        contours = {}
        for key, mesh in meshes.items():
            section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            contours[key] = [] if section is None else section.discrete
        measures = []
        for parent in ['FJ3567', 'candidate']:
            measures.append(dict(parent=parent,
                contour_crossings=sum(crossings(a[:, :2], b[:, :2]) for a in contours[parent] for b in contours['FJ3604']),
                epigastric_vertices_inside_parent=sum(int(Polygon(a[:, :2]).contains_points(b[:, :2]).sum())
                    for a in contours[parent] for b in contours['FJ3604'])))
        rows.append(dict(z_mm=z, measurements=measures,
                         contours_mm={k: [p.tolist() for p in v] for k, v in contours.items()}))
        for key, color, label in [('FJ3567', 'firebrick', 'Original EIA'), ('FJ3604', 'royalblue', 'Original IEA'), ('candidate', 'darkorange', 'Synthetic')]:
            for i, contour in enumerate(contours[key]):
                ax.plot(contour[:, 0], contour[:, 1], color=color, label=label if i == 0 else None)
        ax.set_title(f'Z={z:.1f} mm'); ax.set_aspect('equal'); ax.grid(alpha=.2)
        ax.set_xlabel('L (mm)'); ax.set_ylabel('P (mm)'); ax.legend(fontsize=7)
    fig.suptitle('Actual axial contours: source EIA / IEA and synthetic iliofemoral surface')
    fig.tight_layout()
    out = ROOT/'exports/epigastric-source-junction'; out.mkdir(parents=True, exist_ok=True)
    figure = out/'source-candidate-sections.png'; fig.savefig(figure, dpi=150); plt.close(fig)
    edges = {e['id']: e for e in case['edges']}
    target = np.array(edges['FJ3604:e0']['centerline_mm'][0])
    points = np.array(edges['estimated_R_iliofemoral']['centerline_mm'])
    projections = []
    for index, (a, b) in enumerate(zip(points[:-1], points[1:])):
        direction = b-a
        fraction = float(np.clip((target-a)@direction/(direction@direction), 0, 1))
        point = a+fraction*direction
        projections.append((float(np.linalg.norm(point-target)), index, fraction, point.tolist()))
    distance, index, fraction, point = min(projections)
    locator = dict(edge_id='estimated_R_iliofemoral', interval_index=index, fraction=fraction,
                   position_mm=point, daughter_edge_id='FJ3604:e0', daughter_endpoint='start',
                   endpoint_distance_mm=distance, method='nearest continuous bridge projection of source proximal endpoint',
                   status='REVIEW_LOCATOR_ONLY', anatomical_ostium='UNKNOWN', auto_connect=False)
    report = dict(schema='vv-toolbox.epigastric-source-junction/1', case_revision=revision,
                  source_archive_sha256=atlas.metadata['sha256'],
                  candidate_surface_sha256=surface['sha256'],
                  synthetic_branch_locator=locator,
                  inspection_sha256=hashlib.sha256(inspection_path.read_bytes()).hexdigest(),
                  source_parts=[dict(id=k, name=parts[k]['name'], watertight=bool(meshes[k].is_watertight)) for k in parts],
                  sections=rows, figure=dict(path=figure.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(figure.read_bytes()).hexdigest()),
                  lumen_continuity='UNKNOWN', anatomical_ostium='UNKNOWN',
                  limitation='2D contour intersection witnesses locate surface intersections, not a shared lumen or full 3D intersection extent.')
    (ROOT/'docs/evidence/epigastric-source-junction.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps([dict(z_mm=r['z_mm'], measurements=r['measurements']) for r in rows]))


if __name__ == '__main__':
    main()
