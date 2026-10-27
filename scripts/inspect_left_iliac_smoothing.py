"""Compare fixed-coordinate surface sections and surrounding capsule contacts."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from vv_toolbox.case_io import load_case
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.geometry_quality import screen_nonincident_clearance

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = [ROOT/'exports/synthetic-left-iliac-case/case.snapshot.json',
             ROOT/'exports/synthetic-left-iliac-smoothed/case.snapshot.json']
    raw = [p.read_bytes() for p in paths]
    loaded = [load_case(p) for p in paths]
    check = json.loads((ROOT/'docs/evidence/left-iliac-junction-smoothing.json').read_text())
    assert [r for _, r in loaded] == [check['parent_revision'], check['case_revision']]
    selected = ['FJ3464:e0', 'FJ3466:e0-trim-first']
    out = ROOT/'exports/left-iliac-smoothing-inspection'; out.mkdir(parents=True, exist_ok=True)
    reports, meshes = [], []
    for label, (case, revision) in zip(['before', 'after'], loaded):
        screen = screen_nonincident_clearance(case, [e['id'] for e in case['edges'] if e['centerline_mm'] is not None],
            focus_edge_ids=selected, margin_mm=1.2, max_segment_pairs=2_000_000)
        if screen.get('reason') == 'pair_budget_exhausted':
            raise ValueError('surrounding screen budget exhausted')
        row = dict(label=label, revision=revision, surroundings=screen)
        try:
            vertices, faces, metadata = build_case_surface(case, selected, spacing_mm=.6)
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
            target = out/f'{label}-surface.npz'
            np.savez_compressed(target, vertices_mm=vertices, faces=faces, metadata=np.array(json.dumps(metadata)))
            row['surface'] = dict(status='PASS', vertices=len(vertices), triangles=len(faces), metadata=metadata,
                path=target.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(target.read_bytes()).hexdigest())
        except ValueError as error:
            mesh = None
            row['surface'] = dict(status='FAIL', reason=str(error))
        meshes.append(mesh); reports.append(row)
        print(json.dumps(dict(label=label, surrounding_pairs=len(screen['potential_contacts']), surface=row['surface']['status'])), flush=True)
    pairs = [{tuple(sorted(c['edges'])) for c in r['surroundings']['potential_contacts']} for r in reports]
    result = dict(schema='vv-toolbox.left-iliac-smoothing-inspection/1', selected_edge_ids=selected,
        spacing_mm=.6, margin_mm=1.2, cases=reports,
        new_pairs=[list(p) for p in sorted(pairs[1]-pairs[0])], persistent_pairs=[list(p) for p in sorted(pairs[1]&pairs[0])],
        removed_pairs=[list(p) for p in sorted(pairs[0]-pairs[1])],
        final_mesh_collision='NOT RUN', anatomical_acceptance='UNKNOWN', default_adoption='NOT ACCEPTED')
    if all(m is not None for m in meshes):
        z0 = loaded[0][0]['nodes']['synthetic_L_common_external_iliac']['position_mm'][2]
        fig, axes = plt.subplots(2, 3, figsize=(12, 8)); sections = []
        for ax, offset in zip(axes.flat, [-6., -3., 0., 3., 6., 9.]):
            z = z0+offset; contours_by_case = []
            for label, mesh, color in zip(['before', 'after'], meshes, ['gray', 'firebrick']):
                section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
                contours = [] if section is None else section.discrete
                contours_by_case.append(dict(label=label, contours_mm=[c.tolist() for c in contours]))
                for i, c in enumerate(contours):
                    ax.plot(c[:, 0], c[:, 1], color=color, label=label if i == 0 else None)
            sections.append(dict(z_mm=z, cases=contours_by_case))
            ax.set(title=f'Z={z:.1f} mm', xlabel='L (mm)', ylabel='P (mm)')
            ax.set_aspect('equal'); ax.grid(alpha=.2); ax.legend(fontsize=8)
        fig.suptitle('L iliac junction: actual surfaces at identical fixed axial planes')
        fig.tight_layout(); target = out/'sections.png'; fig.savefig(target, dpi=150); plt.close(fig)
        result.update(sections=sections, figure=dict(path=target.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    assert all(p.read_bytes() == b for p, b in zip(paths, raw))
    result['inputs_unchanged'] = True
    (ROOT/'docs/evidence/left-iliac-smoothing-inspection.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ['new_pairs', 'persistent_pairs', 'removed_pairs']}))


if __name__ == '__main__':
    main()
