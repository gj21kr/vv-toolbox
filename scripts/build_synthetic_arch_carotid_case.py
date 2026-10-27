"""Integrate an inspected arch/LCCA anchor in a separate synthetic candidate."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.access_routes import inspect_route
from vv_toolbox.case_contract import validate_case
from vv_toolbox.case_io import case_digest, load_case, save_case
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.junction_continuity import inspect_bridge_continuity
from vv_toolbox.geometry_quality import screen_nonincident_clearance
from vv_toolbox.synthetic_junctions import split_synthetic_junction
from vv_toolbox.synthetic_routes import extend_synthetic_routes


def store_snapshot(path, case):
    revision = case_digest(case)
    if path.exists():
        if load_case(path)[1] != revision:
            raise ValueError('existing output differs; refusing overwrite')
    else:
        save_case(path, case)
    if load_case(path)[0] != case:
        raise ValueError('snapshot roundtrip mismatch')
    return revision


def main():
    root = Path(__file__).resolve().parents[1]
    out = root/'exports/synthetic-arch-carotid-case'; out.mkdir(parents=True, exist_ok=True)
    parent_path = root/'exports/synthetic-neck-case/case.snapshot.json'
    parent_raw = parent_path.read_bytes(); parent, revision = load_case(parent_path)
    inspection_path = root/'docs/evidence/arch-carotid-junction.json'
    inspection_raw = inspection_path.read_bytes(); inspection = json.loads(inspection_raw)
    source_hashes = {s['id']: s['sha256'] for s in parent['sources']}
    if (source_hashes.get('bp3d') != inspection['source_archive_sha256'] or
            source_hashes.get('bp3d-preview') != inspection['source_preview_sha256'] or
            parent['synthetic_route_inspection']['source_case_sha256'] != inspection['source_case_revision']):
        raise ValueError('parent source identities do not match anchor inspection')
    candidate = inspection['candidate']
    original = {e['id']: e for e in parent['edges']}
    arch = original['FJ3411:e0']
    if (candidate['parent_edge_id'] != arch['id'] or candidate['interval_index'] != 32 or
            candidate['fraction'] != .3576715787251739 or
            candidate['child_edge_id'] != 'FJ3483:e0' or candidate['child_endpoint'] != 'start'):
        raise ValueError('inspected anchor differs from frozen declaration')
    fraction = candidate['fraction']
    p = np.asarray(arch['centerline_mm'])
    anchor = p[32]+fraction*(p[33]-p[32])
    if not np.allclose(anchor, candidate['position_mm'], atol=1e-10, rtol=0):
        raise ValueError('candidate does not interpolate on parent edge')
    children = ['synthetic_arch_before_LCCA', 'synthetic_arch_after_LCCA']
    split_spec = {'schema': 'vv-toolbox.synthetic-junction/1', 'parent_case_sha256': revision,
        'source_hashes': source_hashes, 'edge_id': arch['id'], 'interval_index': 32,
        'fraction': fraction, 'node_id': 'synthetic_arch_LCCA_origin', 'child_edge_ids': children,
        'rationale': candidate['selection_basis'],
        'evidence_refs': ['docs/evidence/arch-carotid-junction.json', 'docs/ARCH_CAROTID_JUNCTION.md']}
    split = split_synthetic_junction(parent, split_spec, case_id='bp3d-arterial-neck-arch-split')
    split_revision = store_snapshot(out/'split-case.snapshot.json', split)
    target = np.asarray(original['FJ3483:e0']['centerline_mm'][0])
    length = float(np.linalg.norm(target-anchor))
    direction = np.asarray(candidate['opening_center_mm'])-anchor
    extension_spec = {'schema': 'vv-toolbox.synthetic-route-extension/1',
        'parent_case_sha256': split_revision, 'bridges': [{
            'id': 'estimated_arch_to_LCCA',
            'from': {'edge_id': children[0], 'endpoint': 'end'},
            'to': {'edge_id': 'FJ3483:e0', 'endpoint': 'start'},
            'attachment_mode': 'side_branch', 'from_radius_mm': 4.,
            'from_direction_xyz': direction.tolist(), 'handle_lengths_mm': [length, length],
            'samples': 96, 'rationale': 'Declared inspected proximal LCCA opening center minus arch anchor direction; source child radius 4 mm, equal endpoint-chord handles, 96 samples. Numerical synthetic branch choice, not anatomical origin approval.',
            'evidence_refs': ['docs/evidence/arch-carotid-junction.json']} ]}
    result = extend_synthetic_routes(split, extension_spec, case_id='bp3d-arterial-neck-arch-LCCA-candidate')
    result_revision = store_snapshot(out/'case.snapshot.json', result)
    by_id = {e['id']: e for e in result['edges']}
    unchanged = all(by_id[e['id']] == e for e in parent['edges'] if e['id'] != arch['id'])
    if not unchanged or parent_path.read_bytes() != parent_raw:
        raise ValueError('parent or unrelated edges changed')
    incidence = validate_case(result)
    required = [children[0], 'estimated_arch_to_LCCA', 'FJ3483:e0', 'estimated_L_carotid_gap', 'FJ1682M:e0']
    route = inspect_route(result, arch['start'], original['FJ1682M:e0']['start'], required)
    continuity = inspect_bridge_continuity(result, max_angle_deg=5., max_radius_jump_mm=1e-6)
    selected = children+['estimated_arch_to_LCCA', 'FJ3483:e0', 'estimated_L_carotid_gap', 'FJ1682M:e0']
    clearance = screen_nonincident_clearance(result, selected, margin_mm=0., max_segment_pairs=1_000_000)
    for contact in clearance['potential_contacts']:
        contact['witness_geometry'] = [
            {'edge_id': ident, 'interval_index': index,
             'points_mm': by_id[ident]['centerline_mm'][index:index+2],
             'radii_mm': by_id[ident]['radii_mm'][index:index+2],
             'anatomy': by_id[ident].get('anatomy'),
             'derivation': by_id[ident].get('derivation')}
            for ident, index in zip(contact['edges'], contact['intervals'])]
    surface_report = {'selected_edge_ids': selected, 'spacing_mm': .6}
    try:
        vertices, faces, metadata = build_case_surface(result, selected, spacing_mm=.6)
        surface_path = out/'surface.npz'
        if not surface_path.exists():
            with surface_path.open('xb') as stream:
                np.savez_compressed(stream, vertices_mm=vertices, faces=faces, metadata=np.array(json.dumps(metadata)))
        surface_report.update(status='PASS', vertices=len(vertices), triangles=len(faces), metadata=metadata)
    except ValueError as error:
        surface_report.update(status='FAIL', reason=str(error), parameters_relaxed=False,
                              surface_published=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 9))
    for ax in axes:
        for ident in selected:
            points = np.asarray(by_id[ident]['centerline_mm'])
            color = 'darkorange' if ident.startswith('estimated') else 'firebrick'
            ax.plot(points[:, 1], points[:, 2], color=color, linewidth=2 if ident.startswith('estimated') else 1, label=ident)
        ax.scatter(anchor[1], anchor[2], c='black', marker='x', s=50)
        ax.scatter(candidate['opening_center_mm'][1], candidate['opening_center_mm'][2], c='royalblue', s=25)
        ax.set_aspect('equal'); ax.grid(alpha=.2); ax.set_xlabel('LPS Y mm'); ax.set_ylabel('LPS Z mm')
    axes[0].set_title('Declared arch → LCCA → neck → ICA graph (projection)')
    axes[1].set(xlim=(anchor[1]-18, anchor[1]+18), ylim=(anchor[2]-15, anchor[2]+30), title='Arch attachment closeup; source opening center blue')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, fontsize=8)
    fig.tight_layout(rect=(0, .12, 1, 1)); figure = out/'arch-carotid-candidate.png'
    fig.savefig(figure, dpi=150); plt.close(fig)
    report = {'schema': 'vv-toolbox.synthetic-arch-carotid-case/1',
        'status': 'PASS', 'scope': 'explicit synthetic graph integration and snapshot preservation only',
        'parent_revision': revision, 'source_case_revision': inspection['source_case_revision'],
        'source_hashes': source_hashes, 'anchor_inspection_sha256': hashlib.sha256(inspection_raw).hexdigest(),
        'split_revision': split_revision, 'derived_revision': result_revision,
        'parent_snapshot_sha256': hashlib.sha256(parent_raw).hexdigest(),
        'split_specification': split_spec, 'extension_specification': extension_spec,
        'parent_snapshot_unchanged': True, 'unrelated_edges_unchanged': unchanged,
        'parent_arch_archived': result['synthetic_junctions']['history'][-1]['parent_edge'] == arch,
        'node_incident_edges': incidence['synthetic_arch_LCCA_origin'],
        'route': route, 'continuity': continuity, 'selected_clearance': clearance,
        'selected_surface': surface_report,
        'default_adoption': 'NOT ACCEPTED', 'anatomical_acceptance': 'UNKNOWN',
        'whole_case_collision': 'NOT RUN', 'femoral_access_combinations': 'NOT RUN',
        'figure': {'path': str(figure.relative_to(root)), 'sha256': hashlib.sha256(figure.read_bytes()).hexdigest()}}
    (out/'split-specification.json').write_text(json.dumps(split_spec, indent=2)+'\n')
    (out/'extension-specification.json').write_text(json.dumps(extension_spec, indent=2)+'\n')
    (root/'docs/evidence/synthetic-arch-carotid-case.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('split_specification', 'extension_specification', 'continuity')}))


if __name__ == '__main__':
    main()
