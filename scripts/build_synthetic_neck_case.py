"""Build explicitly estimated bilateral carotid gaps in a separate source case."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_neck import _terminal
from vv_toolbox.case_io import case_digest, load_case, save_case
from vv_toolbox.geometry_quality import segment_distance, screen_nonincident_clearance
from vv_toolbox.junction_continuity import inspect_bridge_continuity
from vv_toolbox.synthetic_routes import build_synthetic_routes


def main():
    root = Path(__file__).resolve().parents[1]
    source_path = root / 'exports/atlas-case-inspection/all-arterial-case.json'
    raw = source_path.read_bytes()
    source = json.loads(raw)
    inventory = json.loads((root / 'docs/evidence/access-route-endpoints.json').read_text())
    if (case_digest(source) != inventory['source_case_canonical_sha256'] or
            hashlib.sha256(raw).hexdigest() != inventory['source_case_file_sha256']):
        raise ValueError('source case differs from endpoint inspection')
    atlas = load_atlas()
    meshes = {m['id']: m for m in atlas.meshes}
    if atlas.metadata['sha256'] != inventory['source_sha256']:
        raise ValueError('atlas differs from source inspection')
    edges = {e['id']: e for e in source['edges']}
    bridges, comparisons = [], []
    # Endpoint selection is explicit and follows the existing superior-CCA /
    # inferior-ICA convention. This does not adjudicate a carotid bifurcation.
    declarations = [('L', 'FJ3483:e0', 'end', 'FJ1682M:e0', 'end'),
                    ('R', 'FJ3564:e0', 'start', 'FJ1682:e0', 'start')]
    for side, ca, ce, ia, ie in declarations:
        cca, ica = edges[ca], edges[ia]
        p = np.array(source['nodes'][cca[ce]]['position_mm'])
        q = np.array(source['nodes'][ica[ie]]['position_mm'])
        other_c = source['nodes'][cca['start' if ce == 'end' else 'end']]['position_mm']
        other_i = source['nodes'][ica['start' if ie == 'end' else 'end']]['position_mm']
        if not (p[2] > other_c[2] and q[2] < other_i[2] and q[2] > p[2]):
            raise ValueError('explicit anchor no longer matches superior CCA / inferior ICA')
        sections = [_terminal(meshes[cca['source_part_id']], True),
                    _terminal(meshes[ica['source_part_id']], False)]
        length = float(np.linalg.norm(q-p))
        bridges.append({'id': f'estimated_{side}_carotid_gap',
                        'from': {'edge_id': ca, 'endpoint': ce},
                        'to': {'edge_id': ia, 'endpoint': ie},
                        'handle_lengths_mm': [length, length], 'samples': 96,
                        'rationale': 'Existing atlas_neck carotid source pair; superior CCA and inferior ICA extraction endpoints. Handles equal endpoint chord length as existing Hermite display policy. Bifurcation omitted; synthetic continuation only.',
                        'evidence_refs': ['src/vv_toolbox/atlas_neck.py::_repair',
                                          'docs/ACCESS_ROUTE_ENDPOINTS.md',
                                          'docs/evidence/access-route-endpoints.json']})
        comparisons.append({'side': side, 'source_part_ids': [cca['source_part_id'], ica['source_part_id']],
                            'extraction_endpoint_positions_mm': [p.tolist(), q.tolist()],
                            'existing_display_section_centers_mm': [s['center'].tolist() for s in sections],
                            'endpoint_to_section_center_distance_mm': [float(np.linalg.norm(p-sections[0]['center'])), float(np.linalg.norm(q-sections[1]['center']))],
                            'existing_display_section_radii_mm': [s['radius'] for s in sections],
                            'handle_lengths_mm': [length, length],
                            'selection_status': 'explicit synthetic choice, not anatomical approval'})
    spec = {'schema': 'vv-toolbox.synthetic-routes/1',
            'source_case_sha256': case_digest(source), 'bridges': bridges}
    derived = build_synthetic_routes(source, spec, case_id='bp3d-arterial-estimated-carotid-gaps')
    bridge_ids = [b['id'] for b in bridges]
    generated = {e['id']: e for e in derived['edges']}
    a, b = [generated[i] for i in bridge_ids]
    best_distance, best_clearance = float('inf'), float('inf')
    for i, (p, q) in enumerate(zip(a['centerline_mm'], a['centerline_mm'][1:])):
        for j, (u, v) in enumerate(zip(b['centerline_mm'], b['centerline_mm'][1:])):
            distance = segment_distance(p, q, u, v)
            best_distance = min(best_distance, distance)
            best_clearance = min(best_clearance, distance-max(a['radii_mm'][i:i+2])-max(b['radii_mm'][j:j+2]))
    selected = bridge_ids + [item for d in declarations for item in (d[1], d[3])]
    local_screen = screen_nonincident_clearance(derived, selected)
    continuity = inspect_bridge_continuity(derived, max_angle_deg=5., max_radius_jump_mm=1e-6)
    out = root / 'exports/synthetic-neck-case'
    out.mkdir(parents=True, exist_ok=True)
    snapshot = out / 'case.snapshot.json'
    revision = case_digest(derived)
    if snapshot.exists():
        _, old_revision = load_case(snapshot)
        if old_revision != revision:
            raise ValueError('existing neck snapshot differs; refusing overwrite')
    else:
        save_case(snapshot, derived)
    restored, loaded_revision = load_case(snapshot)
    if restored != derived or loaded_revision != revision:
        raise ValueError('neck snapshot roundtrip mismatch')
    if source_path.read_bytes() != raw or derived['nodes'] != source['nodes'] or derived['edges'][:-2] != source['edges']:
        raise ValueError('source preservation failed')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 8))
    for ax, dimensions, label in [(axes[0], (0, 2), 'LPS X/Z'), (axes[1], (1, 2), 'LPS Y/Z')]:
        for ident in selected:
            points = np.array(generated[ident]['centerline_mm'])
            synthetic = ident in bridge_ids
            ax.plot(points[:, dimensions[0]], points[:, dimensions[1]],
                    color='orange' if synthetic else 'firebrick', linewidth=2 if synthetic else 1,
                    label=ident)
        ax.set_aspect('equal'); ax.set_title(label + ' — estimated carotid gaps')
        ax.set_xlabel('mm'); ax.set_ylabel('Z (mm)'); ax.grid(alpha=.2)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=8, loc='lower center', ncol=3)
    fig.tight_layout(rect=(0, .08, 1, 1))
    figure = out / 'carotid-gaps.png'
    fig.savefig(figure, dpi=150); plt.close(fig)
    report = {'schema': 'vv-toolbox.synthetic-neck-case-inspection/1',
              'status': 'PASS', 'scope': 'source preservation and synthetic snapshot generation only',
              'source_case_sha256': spec['source_case_sha256'], 'synthetic_case_sha256': revision,
              'snapshot_path': 'exports/synthetic-neck-case/case.snapshot.json',
              'source_edge_count': len(source['edges']), 'synthetic_edge_count': len(derived['edges']),
              'source_nodes_unchanged': True, 'source_edges_unchanged': True,
              'source_input_bytes_unchanged': True, 'snapshot_roundtrip': 'PASS',
              'source_evidence_status_preserved': True, 'specification': spec,
              'anchor_comparisons': comparisons,
              'bilateral_bridge_minimum_centerline_distance_mm': best_distance,
              'bilateral_bridge_minimum_capsule_clearance_mm': best_clearance,
              'six_edge_nonincident_capsule_screen': local_screen,
              'sampled_bridge_continuity': continuity,
              'whole_atlas_collision': 'NOT RUN', 'junction_surface_smoothness': 'NOT RUN',
              'anatomical_bifurcation': 'OMITTED', 'anatomical_acceptance': 'UNKNOWN',
              'four_access_routes': 'NOT RUN',
              'figure': {'path': 'exports/synthetic-neck-case/carotid-gaps.png',
                         'sha256': hashlib.sha256(figure.read_bytes()).hexdigest()}}
    (root / 'docs/evidence/synthetic-neck-case.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    (root / 'docs/evidence/synthetic-neck-specification.json').write_text(json.dumps(spec, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('specification', 'anchor_comparisons', 'six_edge_nonincident_capsule_screen', 'sampled_bridge_continuity')}))
    print(json.dumps(local_screen))
    print(json.dumps(continuity))


if __name__ == '__main__':
    main()
