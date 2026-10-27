"""Fixed centerline-then-radius experiment with four-way matched-plane measures."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from inspect_centerline_regularized_neck import fixed_planes
from inspect_neck_surface_bulge import inspect
from vv_toolbox.case_io import case_digest, load_case, save_case
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.centerline_regularization import smooth_synthetic_centerlines
from vv_toolbox.radius_regularization import smooth_synthetic_radii
from vv_toolbox.geometry_quality import screen_nonincident_clearance
from vv_toolbox.junction_continuity import inspect_bridge_continuity


def read_mesh(path, revision):
    with np.load(path, allow_pickle=False) as data:
        metadata = json.loads(str(data['metadata']))
        if metadata['case_revision'] != revision:
            raise ValueError('surface case revision mismatch')
        return trimesh.Trimesh(vertices=data['vertices_mm'], faces=data['faces'], process=False), metadata


def main():
    root = Path(__file__).resolve().parents[1]
    folder = root / 'exports/synthetic-neck-case'
    source = folder / 'case.snapshot.json'
    before_bytes = source.read_bytes()
    original, revision = load_case(source)
    ids = ['FJ3483:e0', 'FJ1682M:e0', 'FJ3564:e0', 'FJ1682:e0']
    selected = original['synthetic_route_inspection']['bridge_ids']+ids
    centerline_parameters = dict(sigma_mm=2., sample_spacing_mm=.25, max_displacement_mm=1.)
    radius_parameters = dict(sigma_mm=2., sample_spacing_mm=.25, max_change_mm=1.)
    report = {'schema': 'vv-toolbox.joint-neck-experiment/1', 'parent_revision': revision,
              'centerline_parameters': centerline_parameters, 'radius_parameters': radius_parameters,
              'operator_order': ['centerline', 'radius'], 'parameters_relaxed': False,
              'normal_half_window_mm': 2., 'surface_spacing_mm': .6,
              'default_adoption': 'NOT ACCEPTED', 'anatomical_acceptance': 'UNKNOWN',
              'surface_smoothness_acceptance': 'UNKNOWN'}
    try:
        centerline = smooth_synthetic_centerlines(original, ids, **centerline_parameters,
            case_id='bp3d-arterial-carotid-centerline-regularized')
        joint = smooth_synthetic_radii(centerline, ids, **radius_parameters,
            case_id='bp3d-arterial-carotid-joint-regularized')
        snapshot = folder / 'joint-case.snapshot.json'
        if snapshot.exists():
            if load_case(snapshot)[1] != case_digest(joint):
                raise ValueError('existing joint snapshot differs')
        else:
            save_case(snapshot, joint)
        all_geometry = [e['id'] for e in joint['edges'] if e['centerline_mm'] is not None]
        baseline_path = root / 'docs/evidence/centerline-regularized-neck.json'
        baseline_raw = baseline_path.read_bytes()
        baseline = json.loads(baseline_raw)
        if baseline['parent_revision'] != revision:
            raise ValueError('baseline clearance parent hash mismatch')
        baseline_screen = baseline['baseline_same_scope_capsules']
        coverage = baseline_screen['coverage']
        if (set(coverage['selected_edge_ids']) != set(all_geometry) or
                set(coverage['focus_edge_ids']) != set(selected) or
                baseline_screen.get('reason') == 'pair_budget_exhausted'):
            raise ValueError('baseline clearance scope/budget mismatch')
        report['baseline_evidence'] = {'path': str(baseline_path.relative_to(root)),
            'sha256': hashlib.sha256(baseline_raw).hexdigest(), 'parent_revision': revision,
            'baseline_screen': baseline_screen}
        after = screen_nonincident_clearance(joint, all_geometry,
            focus_edge_ids=selected, max_segment_pairs=2_000_000)
        before_pairs = {tuple(sorted(c['edges'])) for c in baseline_screen['potential_contacts']}
        after_pairs = {tuple(sorted(c['edges'])) for c in after['potential_contacts']}
        report['modified_edge_capsules'] = after
        report['contact_pair_changes'] = {'new_pairs': sorted(after_pairs-before_pairs),
            'persisting_pairs': sorted(after_pairs & before_pairs),
            'no_longer_detected_pairs': sorted(before_pairs-after_pairs),
            'interpretation': 'capsule potential contacts, not exact surface collisions'}
        report['continuity'] = inspect_bridge_continuity(joint, max_angle_deg=5., max_radius_jump_mm=1e-6)
        surface = folder / 'joint-neck-surface.npz'
        if not surface.exists():
            vertices, faces, metadata = build_case_surface(joint, selected, spacing_mm=.6)
            with surface.open('xb') as stream:
                np.savez_compressed(stream, vertices_mm=vertices, faces=faces, metadata=np.array(json.dumps(metadata)))
        variants = {
            'original': (source, folder/'neck-surface.npz'),
            'centerline_only': (folder/'centerline-regularized-case.snapshot.json', folder/'centerline-regularized-neck-surface.npz'),
            'radius_only': (folder/'regularized-case.snapshot.json', folder/'regularized-neck-surface.npz'),
            'joint': (snapshot, surface)}
        reference = inspect(source, folder/'neck-surface.npz', 2.)
        measures = {}
        for name, (case_path, surface_path) in variants.items():
            variant, variant_revision = load_case(case_path)
            if variant['sources'] != original['sources'] or variant['base_model_id'] != original['base_model_id']:
                raise ValueError('comparison variant uses a different source model')
            if name == 'centerline_only' and variant_revision != case_digest(centerline):
                raise ValueError('centerline-only variant does not match fixed operator')
            if name == 'radius_only':
                expected_radius = smooth_synthetic_radii(original, ids, **radius_parameters,
                    case_id=variant['case_id'])
                if case_digest(expected_radius) != variant_revision:
                    raise ValueError('radius-only variant does not match fixed operator')
            mesh, metadata = read_mesh(surface_path, variant_revision)
            fixed = fixed_planes(mesh, reference)
            own = inspect(case_path, surface_path, 2.)
            measures[name] = {'case_revision': variant_revision,
                'snapshot_sha256': hashlib.sha256(case_path.read_bytes()).hexdigest(),
                'surface_sha256': hashlib.sha256(surface_path.read_bytes()).hexdigest(),
                'fixed_original_planes': fixed, 'own_planes': own,
                'topology': metadata['checks']}
        comparisons = []
        for i, attachment in enumerate(reference['attachments']):
            comparisons.append({'edge_id': attachment['source_edge_id'],
                'fixed_original_plane_tv_mm': {name: m['fixed_original_planes'][i]['source_side_surface_total_variation_mm'] for name, m in measures.items()},
                'own_plane_tv_mm': {name: m['own_planes']['attachments'][i]['source_side_surface_total_variation_mm'] for name, m in measures.items()}})
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
        colors = {'original': 'black', 'centerline_only': 'royalblue', 'radius_only': 'firebrick', 'joint': 'green'}
        for i, ax in enumerate(axes.flat):
            for name, measure in measures.items():
                stations = measure['fixed_original_planes'][i]['stations']
                ax.plot([s['offset_from_attachment_mm'] for s in stations],
                    [s['section']['equivalent_radius_mm'] for s in stations], label=name, color=colors[name])
            ax.axvline(0, color='orange', linestyle='--')
            ax.set_title(comparisons[i]['edge_id']); ax.set_xlabel('Original arc offset (mm)')
            ax.set_ylabel('Fixed-plane equivalent radius (mm)'); ax.legend(fontsize=8); ax.grid(alpha=.2)
        fig.tight_layout(); figure = folder/'joint-four-way-comparison.png'
        fig.savefig(figure, dpi=150); plt.close(fig)
        report.update(status='PASS', scope='fixed operators, generated surface and four-way measurements only',
            derived_revision=case_digest(joint), centerline_metrics=joint['centerline_regularization']['metrics'],
            radius_metrics=joint['radius_regularization']['metrics'], matched_plane_count=reference['station_count'],
            comparisons=comparisons, measurements=measures,
            figure={'path': str(figure.relative_to(root)), 'sha256': hashlib.sha256(figure.read_bytes()).hexdigest()})
    except ValueError as error:
        report.update(status='FAIL', reason=str(error))
    if source.read_bytes() != before_bytes:
        raise ValueError('original snapshot changed')
    report['original_snapshot_unchanged'] = True
    (root/'docs/evidence/joint-regularized-neck.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('measurements', 'baseline_evidence', 'modified_edge_capsules')}))


if __name__ == '__main__':
    main()
