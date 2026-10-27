"""Native CIA/EIA/IIA sections and explicit synthetic branch review locator."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from inspect_brachiocephalic_junction import crossings

ROOT = Path(__file__).resolve().parents[1]


def main():
    case, revision = load_case(ROOT/'exports/synthetic-right-iliac-case/case.snapshot.json')
    atlas = load_atlas()
    assert atlas.metadata['sha256'] == next(s['sha256'] for s in case['sources'] if s['id'] == 'bp3d')
    parts = {p['id']: p for p in atlas.meshes if p['id'] in ['FJ3565', 'FJ3567', 'FJ3569']}
    meshes = {k: trimesh.Trimesh(vertices=p['vertices'], faces=p['faces'], process=False) for k, p in parts.items()}
    fig, axes = plt.subplots(2, 3, figsize=(12, 8)); records = []
    for ax, z in zip(axes.flat, [903., 906., 909., 912., 915., 924.]):
        sections = {}
        for ident, mesh in meshes.items():
            section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            sections[ident] = [] if section is None else section.discrete
        metrics = {parent: sum(crossings(a[:, :2], b[:, :2]) for a in sections[parent] for b in sections['FJ3569'])
                   for parent in ['FJ3565', 'FJ3567']}
        records.append(dict(z_mm=z, internal_iliac_crossings=metrics,
                            contours_mm={k: [p.tolist() for p in v] for k, v in sections.items()}))
        for ident, label, color in [('FJ3565', 'CIA', 'firebrick'), ('FJ3567', 'EIA', 'darkorange'), ('FJ3569', 'IIA', 'royalblue')]:
            for i, c in enumerate(sections[ident]):
                ax.plot(c[:, 0], c[:, 1], color=color, label=label if i == 0 else None)
        ax.set(title=f'Z={z:.1f} mm', xlabel='L (mm)', ylabel='P (mm)')
        ax.set_aspect('equal'); ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.suptitle('Right iliac source surfaces: actual axial contours')
    fig.tight_layout()
    out = ROOT/'exports/internal-iliac-junction'; out.mkdir(parents=True, exist_ok=True)
    figure = out/'source-sections.png'; fig.savefig(figure, dpi=150); plt.close(fig)
    edges = {e['id']: e for e in case['edges']}
    points = np.array(edges['estimated_R_CIA_EIA_continuation']['centerline_mm'])
    target = np.array(edges['FJ3569:e0']['centerline_mm'][-1])
    locations = []
    for i, (a, b) in enumerate(zip(points[:-1], points[1:])):
        u = b-a; fraction = float(np.clip((target-a)@u/(u@u), 0., 1.)); point = a+fraction*u
        locations.append((float(np.linalg.norm(point-target)), i, fraction, point.tolist()))
    distance, index, fraction, point = min(locations)
    locator = dict(edge_id='estimated_R_CIA_EIA_continuation', interval_index=index, fraction=fraction,
        position_mm=point, daughter_edge_id='FJ3569:e0', daughter_endpoint='end', endpoint_distance_mm=distance,
        status='REVIEW_LOCATOR_ONLY', anatomical_ostium='UNKNOWN')
    report = dict(schema='vv-toolbox.internal-iliac-junction-review/1', case_revision=revision,
        source_archive_sha256=atlas.metadata['sha256'], sections=records, synthetic_branch_locator=locator,
        figure=dict(path=figure.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(figure.read_bytes()).hexdigest()),
        lumen_continuity='UNKNOWN', anatomical_acceptance='UNKNOWN')
    (ROOT/'docs/evidence/internal-iliac-junction-review.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(locator=locator, sections=[dict(z_mm=r['z_mm'], crossings=r['internal_iliac_crossings']) for r in records])))


if __name__ == '__main__':
    main()
