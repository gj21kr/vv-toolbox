"""Fixed-parameter actual neck radius experiment; preserve all prior outputs."""
import argparse
import json
from pathlib import Path

import numpy as np

from inspect_neck_surface_bulge import inspect
from vv_toolbox.case_io import case_digest, load_case, save_case
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.radius_regularization import smooth_synthetic_radii


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--normal-half-window-mm', type=float, default=.3)
    parser.add_argument('--output', default='docs/evidence/regularized-neck-surface.json')
    parser.add_argument('--figure', default='exports/synthetic-neck-case/regularized-radius-comparison.png')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    folder = root / 'exports/synthetic-neck-case'
    original_path = folder / 'case.snapshot.json'
    original_bytes = original_path.read_bytes()
    original, revision = load_case(original_path)
    source_edges = ['FJ3483:e0', 'FJ1682M:e0', 'FJ3564:e0', 'FJ1682:e0']
    parameters = {'sigma_mm': 2., 'sample_spacing_mm': .25, 'max_change_mm': 1.}
    report_path = root / args.output
    try:
        derived = smooth_synthetic_radii(original, source_edges, **parameters,
            case_id='bp3d-arterial-estimated-carotid-gaps-radius-regularized')
    except ValueError as exc:
        report_path.write_text(json.dumps({'status': 'FAIL', 'parameters': parameters,
            'parent_revision': revision, 'reason': str(exc), 'parameters_relaxed': False}, indent=2)+'\n')
        raise
    snapshot = folder / 'regularized-case.snapshot.json'
    if snapshot.exists():
        _, existing = load_case(snapshot)
        if existing != case_digest(derived):
            raise ValueError('existing regularized snapshot differs')
    else:
        save_case(snapshot, derived)
    selected = original['synthetic_route_inspection']['bridge_ids']+source_edges
    surface = folder / 'regularized-neck-surface.npz'
    if not surface.exists():
        vertices, faces, metadata = build_case_surface(derived, selected, spacing_mm=.6)
        with surface.open('xb') as stream:
            np.savez_compressed(stream, vertices_mm=vertices, faces=faces, metadata=np.array(json.dumps(metadata)))
    before = inspect(original_path, folder / 'neck-surface.npz', args.normal_half_window_mm)
    after = inspect(snapshot, surface, args.normal_half_window_mm)
    comparisons = []
    for a, b in zip(before['attachments'], after['attachments']):
        if a['source_edge_id'] != b['source_edge_id']:
            raise ValueError('station ordering differs')
        for x, y in zip(a['stations'], b['stations']):
            if x['center_mm'] != y['center_mm'] or x['normal'] != y['normal']:
                raise ValueError('comparison plane changed')
        comparisons.append({'edge_id': a['source_edge_id'],
            'before_profile_tv_mm': a['source_side_profile_total_variation_mm'],
            'after_profile_tv_mm': b['source_side_profile_total_variation_mm'],
            'before_surface_tv_mm': a['source_side_surface_total_variation_mm'],
            'after_surface_tv_mm': b['source_side_surface_total_variation_mm']})
    if original_path.read_bytes() != original_bytes:
        raise ValueError('original snapshot changed')
    report = {'status': 'PASS', 'scope': 'fixed-parameter synthetic transformation and matched-plane measurement only',
        'parameters': parameters, 'parameters_relaxed': False, 'parent_revision': revision,
        'normal_half_window_mm': args.normal_half_window_mm,
        'derived_revision': case_digest(derived), 'original_snapshot_unchanged': True,
        'centerlines_unchanged': all(a['centerline_mm'] == b['centerline_mm'] for a, b in zip(original['edges'], derived['edges'])),
        'radius_metrics': derived['radius_regularization']['metrics'],
        'matched_plane_count': before['station_count'], 'comparisons': comparisons,
        'before': before, 'after': after, 'anatomical_acceptance': 'UNKNOWN',
        'whole_atlas_collision_after_change': 'NOT RUN', 'surface_smoothness_acceptance': 'UNKNOWN'}
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    for ax, a, b in zip(axes.flat, before['attachments'], after['attachments']):
        for row, label, color in [(a, 'Before mesh', 'firebrick'), (b, 'After mesh', 'navy')]:
            ax.plot([s['offset_from_attachment_mm'] for s in row['stations']],
                    [s['section']['equivalent_radius_mm'] for s in row['stations']], label=label, color=color)
        ax.axvline(0, color='orange', linestyle='--')
        ax.set_title(a['source_edge_id']); ax.set_xlabel('Arc offset from attachment (mm)')
        ax.set_ylabel('Area-equivalent radius (mm)'); ax.grid(alpha=.2); ax.legend()
    fig.tight_layout()
    figure = root / args.figure
    fig.savefig(figure, dpi=150); plt.close(fig)
    report['figure_path'] = args.figure
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('before', 'after')}))


if __name__ == '__main__':
    main()
