"""Read-only topology inspection and attachment closeups of generated mesh."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', default='exports/synthetic-neck-case/case.snapshot.json')
    parser.add_argument('--surface', default='exports/synthetic-neck-case/neck-surface.npz')
    parser.add_argument('--output', default='docs/evidence/synthetic-neck-surface.json')
    parser.add_argument('--figure', default='exports/synthetic-neck-case/neck-surface-attachments.png')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    folder = root / 'exports/synthetic-neck-case'
    path = root / args.surface
    before = path.read_bytes()
    case, revision = load_case(root / args.snapshot)
    with np.load(path, allow_pickle=False) as data:
        v, f = data['vertices_mm'], data['faces']
        metadata = json.loads(str(data['metadata']))
    if metadata['case_revision'] != revision:
        raise ValueError('surface does not match synthetic snapshot')
    mesh = trimesh.Trimesh(vertices=v, faces=f, process=False)
    components = mesh.split(only_watertight=False)
    topology = [{'vertices': len(m.vertices), 'triangles': len(m.faces),
                 'watertight': bool(m.is_watertight), 'winding_consistent': bool(m.is_winding_consistent),
                 'positive_volume': bool(m.is_volume), 'volume_mm3': float(m.volume),
                 'euler_number': int(m.euler_number)} for m in components]
    if len(components) != metadata['graph_component_count'] or not all(
            row['watertight'] and row['winding_consistent'] and row['positive_volume'] for row in topology):
        raise ValueError('stored mesh topology disagrees with graph components')
    by_id = {e['id']: e for e in case['edges']}
    attachments = []
    for bridge_id in case['synthetic_route_inspection']['bridge_ids']:
        edge = by_id[bridge_id]
        for endpoint in ['start', 'end']:
            attachments.append({'bridge_id': bridge_id, 'endpoint': endpoint,
                                'node_id': edge[endpoint],
                                'position_mm': case['nodes'][edge[endpoint]]['position_mm']})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(12, 11))
    centers = mesh.triangles_center
    light = np.array([1., -1., 1.]); light /= np.linalg.norm(light)
    shade = .35+.65*np.abs(mesh.face_normals @ light)
    for index, attachment in enumerate(attachments):
        ax = fig.add_subplot(2, 2, index+1, projection='3d')
        center = np.array(attachment['position_mm'])
        # This is a local display crop only; topology was measured on full mesh.
        selected = np.max(np.abs(centers-center), axis=1) <= 15
        triangles = v[f[selected]]
        if not len(triangles):
            raise ValueError('no surface triangles near attachment')
        colors = np.column_stack([.85*shade[selected], .18*shade[selected], .22*shade[selected], np.ones(selected.sum())])
        ax.add_collection3d(Poly3DCollection(triangles, facecolors=colors, edgecolors='none'))
        ax.scatter(*center, color='gold', s=25, depthshade=False)
        ax.plot([center[0]-12, center[0]+12], [center[1], center[1]],
                [center[2], center[2]], color='goldenrod', linestyle='--', linewidth=1.5)
        for j, setter in enumerate([ax.set_xlim, ax.set_ylim, ax.set_zlim]):
            setter(center[j]-15, center[j]+15)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=18, azim=-65)
        ax.set_title(attachment['bridge_id']+' / '+attachment['endpoint'], fontsize=10)
        ax.set_xlabel('LPS X mm'); ax.set_ylabel('LPS Y mm'); ax.set_zlabel('LPS Z mm')
        attachment['local_display_triangle_count'] = int(selected.sum())
    fig.suptitle('Generated six-edge surface: attachment closeups\nGold line crosses attachment coordinate; displayed crops are not mesh boundaries', fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, .94))
    figure = root / args.figure
    fig.savefig(figure, dpi=150); plt.close(fig)
    if path.read_bytes() != before:
        raise ValueError('surface input changed during inspection')
    report = {'schema': 'vv-toolbox.synthetic-neck-surface-inspection/1',
        'status': 'PASS', 'scope': 'stored six-edge synthetic mesh topology and local rendered closeups',
        'surface_file_sha256': hashlib.sha256(before).hexdigest(), 'case_revision': revision,
        'selected_edge_ids': metadata['edge_ids'], 'spacing_mm': metadata['spacing_mm'],
        'vertices': len(v), 'triangles': len(f), 'graph_component_count': metadata['graph_component_count'],
        'mesh_component_count': len(components), 'components': topology, 'attachments': attachments,
        'input_bytes_unchanged': True, 'anatomical_acceptance': 'UNKNOWN',
        'surface_smoothness': 'NOT RUN', 'final_surface_collision': 'NOT RUN',
        'source_surface_union': 'NOT RUN', 'full_case_surface': 'NOT RUN',
        'figure': {'path': args.figure,
                   'sha256': hashlib.sha256(figure.read_bytes()).hexdigest()}}
    (root / args.output).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('attachments', 'selected_edge_ids')}))


if __name__ == '__main__':
    main()
