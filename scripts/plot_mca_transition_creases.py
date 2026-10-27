"""Locate measured creases in three orthographic projections."""
import hashlib
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', default='mca-tangent-transition-normal',
                        choices=['mca-tangent-transition-normal',
                                 'mca-tangent-transition-constant-earcut-flips'])
    name = parser.parse_args().candidate
    evidence_path = ROOT/'docs/evidence'/f'{name}.json'
    evidence = json.loads(evidence_path.read_text())
    path = ROOT/'exports'/name/'surface.npz'
    if hashlib.sha256(path.read_bytes()).hexdigest() != evidence['artifact_sha256']:
        raise ValueError('candidate hash mismatch')
    with np.load(path, allow_pickle=False) as data:
        v, f = data['vertices_mm'], data['faces']
        meta = json.loads(str(data['metadata'].item()))
    neck = json.loads((ROOT/'docs/evidence/regularized-mca-sac.json').read_text())['specification']['neck']
    basis = np.column_stack([neck[k] for k in ('width_axis', 'depth_axis', 'normal')])
    local = (v-np.array(neck['center_mm']))@basis
    mesh = trimesh.Trimesh(vertices=v, faces=f, process=False)
    patch = np.asarray(meta['face_origin_labels']) == 4
    edges = np.unique(np.sort(np.concatenate([f[patch][:, [0, 1]],
                                              f[patch][:, [1, 2]],
                                              f[patch][:, [2, 0]]]), axis=1), axis=0)
    selected = (np.degrees(mesh.face_adjacency_angles) > 90) & patch[mesh.face_adjacency].any(axis=1)
    bad = mesh.face_adjacency_edges[selected]
    rim = local[meta['design_vertex_ids']]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (i, j), title in zip(axes, [(0, 1), (0, 2), (1, 2)],
                                 ['Width / depth', 'Width / normal', 'Depth / normal']):
        ax.add_collection(LineCollection(local[edges][:, :, [i, j]], colors='#b7c1cd',
                                          linewidths=.25))
        ax.add_collection(LineCollection(local[bad][:, :, [i, j]], colors='#d62828',
                                          linewidths=1.4))
        closed = np.vstack([rim, rim[0]])
        ax.plot(closed[:, i], closed[:, j], color='#147d92', linewidth=1)
        ax.autoscale()
        ax.set_aspect('equal')
        ax.set_title(title)
        ax.set_xlabel('mm')
        ax.set_ylabel('mm')
    fig.suptitle('Candidate: red edges >90 degrees; cyan design neck; not accepted')
    fig.tight_layout()
    image = path.parent/'creases.png'
    fig.savefig(image, dpi=150)
    plt.close(fig)
    evidence['crease_figure_sha256'] = hashlib.sha256(image.read_bytes()).hexdigest()
    evidence_path.write_text(json.dumps(evidence, indent=2)+'\n')


if __name__ == '__main__':
    main()
