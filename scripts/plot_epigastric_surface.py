"""Render actual sections of the inspected compound-junction surface."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT/'exports/epigastric-candidate-inspection/surface.npz'
    with np.load(path) as data:
        mesh = trimesh.Trimesh(vertices=data['vertices_mm'], faces=data['faces'], process=False)
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    records = []
    for ax, z in zip(axes.flat, [826., 829., 832., 835., 838., 841.]):
        section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        contours = [] if section is None else section.discrete
        for c in contours:
            ax.plot(c[:, 0], c[:, 1], color='firebrick')
        ax.set(title=f'Z={z:.1f} mm', xlabel='L (mm)', ylabel='P (mm)')
        ax.set_aspect('equal'); ax.grid(alpha=.2)
        records.append(dict(z_mm=z, contours_mm=[c.tolist() for c in contours]))
    fig.suptitle('Generated IEA compound junction: actual surface sections')
    fig.tight_layout()
    target = path.parent/'sections.png'; fig.savefig(target, dpi=150); plt.close(fig)
    record = dict(schema='vv-toolbox.epigastric-surface-sections/1',
                  surface_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  figure=dict(path=target.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(target.read_bytes()).hexdigest()),
                  sections=records, anatomical_acceptance='UNKNOWN')
    (ROOT/'docs/evidence/epigastric-surface-sections.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(dict(figure=record['figure'], contours=[len(r['contours_mm']) for r in records])))


if __name__ == '__main__':
    main()
