"""Read generated meshes and refine the new surrounding contact witness."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from vv_toolbox.case_io import load_case
from vv_toolbox.geometry_quality import segment_distance

ROOT = Path(__file__).resolve().parents[1]


def main():
    case, revision = load_case(ROOT/'exports/synthetic-iliofemoral-case/case.snapshot.json')
    report_path = ROOT/'docs/evidence/iliofemoral-candidate-inspection.json'
    inspection = json.loads(report_path.read_text())
    assert revision == inspection['candidate_revision']
    edges = {e['id']: e for e in case['edges']}
    contacts = []
    for row in inspection['bridge_surrounding_contacts']:
        a, b = [edges[i] for i in row['edges']]
        p, q = np.array(a['centerline_mm']), np.array(b['centerline_mm'])
        ra, rb = np.array(a['radii_mm']), np.array(b['radii_mm'])
        best = (float('inf'), -1, -1)
        for i in range(len(p)-1):
            for j in range(len(q)-1):
                clearance = segment_distance(p[i], p[i+1], q[j], q[j+1])-max(ra[i:i+2])-max(rb[j:j+2])
                best = min(best, (float(clearance), i, j))
        contacts.append(dict(edges=row['edges'], names=[a['anatomy']['artery'], b['anatomy']['artery']],
                             minimum_capsule_clearance_lower_bound_mm=best[0], intervals=list(best[1:]),
                             tested_interval_pairs=(len(p)-1)*(len(q)-1),
                             zero_margin_status='PASS' if best[0] > 0 else 'UNKNOWN',
                             original_1_2mm_margin_status='PASS' if best[0] > 1.2 else 'UNKNOWN'))
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    sections = []
    for row, surface in enumerate(inspection['surfaces']):
        assert surface['status'] == 'PASS'
        path = ROOT/surface['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == surface['sha256']
        with np.load(path) as data:
            mesh = trimesh.Trimesh(vertices=data['vertices_mm'], faces=data['faces'], process=False)
        side = surface['side']
        bridge = np.array(edges[f'estimated_{side}_iliofemoral']['centerline_mm'])
        for col, index in enumerate([0, len(bridge)//2, len(bridge)-1]):
            z = float(bridge[index, 2])
            section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            contours = [] if section is None else section.discrete
            sections.append(dict(side=side, z_mm=z, contours_mm=[c.tolist() for c in contours]))
            ax = axes[row, col]
            for contour in contours:
                ax.plot(contour[:, 0], contour[:, 1], color='firebrick')
            ax.set_title(f'{side} / Z={z:.2f} mm')
            ax.set_aspect('equal'); ax.grid(alpha=.2)
            ax.set_xlabel('L (mm)'); ax.set_ylabel('P (mm)')
    fig.suptitle('Generated iliofemoral surfaces: actual axial sections, not anatomical acceptance')
    fig.tight_layout()
    path = ROOT/'exports/iliofemoral-candidate-inspection/sections.png'
    fig.savefig(path, dpi=150); plt.close(fig)
    result = dict(schema='vv-toolbox.iliofemoral-surface-sections/1', case_revision=revision,
                  inspection_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
                  contacts=contacts, sections=sections,
                  figure=dict(path=path.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest()),
                  limitation='Do not replace the original 1.2 mm margin gate with this zero-margin diagnostic.',
                  anatomical_acceptance='UNKNOWN', final_mesh_collision='NOT RUN')
    (ROOT/'docs/evidence/iliofemoral-surface-sections.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(contacts))


if __name__ == '__main__':
    main()
