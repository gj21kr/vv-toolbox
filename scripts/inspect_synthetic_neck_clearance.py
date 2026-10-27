"""Audit existing neck estimates against all available arterial source paths."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case
from vv_toolbox.geometry_quality import (screen_nonincident_clearance,
    screen_junction_clearance, screen_self_clearance)


def main():
    root = Path(__file__).resolve().parents[1]
    path = root / 'exports/synthetic-neck-case/case.snapshot.json'
    before = path.read_bytes()
    case, revision = load_case(path)
    by_id = {e['id']: e for e in case['edges']}
    bridges = case['synthetic_route_inspection']['bridge_ids']
    selected = [e['id'] for e in case['edges'] if e['centerline_mm'] is not None]
    missing = [e['id'] for e in case['edges'] if e['centerline_mm'] is None]
    margin, spacing, budget = 0., .6, 2_000_000
    nonincident = screen_nonincident_clearance(case, selected, margin_mm=margin,
        max_segment_pairs=budget, focus_edge_ids=bridges)
    incident = []
    for bridge_id in bridges:
        bridge = by_id[bridge_id]
        for edge in case['edges']:
            if edge['id'] == bridge_id:
                continue
            shared = {bridge['start'], bridge['end']} & {edge['start'], edge['end']}
            if not shared:
                continue
            if edge['centerline_mm'] is None or edge['start'] == edge['end']:
                incident.append({'edges': [bridge_id, edge['id']], 'status': 'UNKNOWN',
                                 'reason': 'missing_or_closed_incident_path'})
                continue
            collars = {}
            for node in shared:
                radii = [e['radii_mm'][0 if e['start'] == node else -1]
                         for e in case['edges'] if e['centerline_mm'] is not None and
                         node in (e['start'], e['end'])]
                collars[node] = 3*max(radii)+2*spacing
            result = screen_junction_clearance(case, [bridge_id, edge['id']],
                collars_mm=collars, margin_mm=margin, max_segment_pairs=budget)
            incident.append({'edges': [bridge_id, edge['id']], **result})
    windows = {ident: 4*max(by_id[ident]['radii_mm'])+2*spacing for ident in bridges}
    self_report = screen_self_clearance(case, bridges, local_windows_mm=windows,
        margin_mm=margin, max_segment_pairs=budget)

    def evidence(ident, interval=None, arc_interval=None):
        edge = by_id[ident]
        row = {k: edge.get(k) for k in ('id', 'source_part_id', 'source_ids', 'identity_refs',
                                       'geometry_kind', 'evidence_status', 'anatomy', 'derivation')}
        if interval is not None:
            row.update(interval_index=interval, points_mm=edge['centerline_mm'][interval:interval+2],
                       radii_mm=edge['radii_mm'][interval:interval+2])
        if arc_interval is not None:
            p = np.asarray(edge['centerline_mm'])
            arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
            row.update(arc_interval_mm=arc_interval,
                points_mm=np.column_stack([np.interp(arc_interval, arc, p[:, j]) for j in range(3)]).tolist(),
                radii_mm=np.interp(arc_interval, arc, edge['radii_mm']).tolist())
        return row

    witnesses = []
    for finding in nonincident.get('potential_contacts', []):
        witnesses.append({'check': 'nonincident', 'finding': finding,
            'edges': [evidence(ident, interval=i) for ident, i in zip(finding['edges'], finding['intervals'])]})
    for result in incident:
        for finding in result.get('potential_contacts', []):
            witnesses.append({'check': 'junction_outside_collar', 'finding': finding,
                'edges': [evidence(ident, arc_interval=arc) for ident, arc in zip(finding['edges'], finding['arc_intervals_mm'])]})
    for finding in self_report.get('potential_contacts', []):
        witnesses.append({'check': 'bridge_self', 'finding': finding,
            'edges': [evidence(finding['edge_id'], interval=i) for i in finding['intervals']]})
    statuses = [nonincident['status'], self_report['status']] + [r['status'] for r in incident]
    if path.read_bytes() != before:
        raise ValueError('snapshot changed during inspection')
    report = {'schema': 'vv-toolbox.synthetic-neck-clearance/1',
        'status': 'PASS' if not missing and all(s == 'PASS' for s in statuses) else 'UNKNOWN',
        'scope': 'two generated bridges versus all available source arterial centerline capsules, bridge incident paths outside collars and nonlocal self clearance',
        'snapshot_revision': revision, 'snapshot_file_sha256': hashlib.sha256(before).hexdigest(),
        'source_case_sha256': case['generation']['config']['source_case_sha256'],
        'generation_seed': case['generation']['seed'], 'random_sampling': False,
        'thresholds': {'margin_mm': margin, 'nominal_surface_spacing_mm': spacing,
                       'collar_policy': '3 * maximum incident endpoint radius + 2 * spacing',
                       'self_window_policy': '4 * maximum bridge radius + 2 * spacing',
                       'max_segment_pairs_per_screen': budget,
                       'interpretation': 'numerical conservative screening, not clinical tolerance'},
        'input_edge_count': len(case['edges']), 'geometry_edge_count': len(selected),
        'missing_geometry_edge_ids': missing, 'focus_bridge_ids': bridges,
        'source_parts_without_paths': case.get('inspection', {}).get('missing_path_parts', []),
        'excluded_source_extraction_edges': [r['edge_id'] for r in case.get('inspection', {}).get('rejected_extraction_edges', [])],
        'whole_atlas_coverage': 'UNKNOWN: selected extracted arterial paths only; missing parts, excluded extraction artifacts and other circulation layers are not covered',
        'nonincident': nonincident, 'incident': incident, 'self': self_report,
        'contact_witnesses': witnesses, 'input_bytes_unchanged': True, 'automatic_repairs': [],
        'all_source_to_source_clearance': 'NOT RUN', 'inside_junction_collars': 'NOT CHECKED',
        'local_bridge_folding': 'NOT CHECKED', 'final_surface_collision': 'NOT RUN',
        'anatomical_acceptance': 'UNKNOWN'}
    target = root / 'docs/evidence/synthetic-neck-clearance.json'
    target.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'status': report['status'], 'input_edges': len(case['edges']),
        'missing_geometry': missing, 'nonincident_status': nonincident['status'],
        'nonincident_checked_segments': nonincident.get('checked_segment_pairs'),
        'nonincident_bbox_pairs': nonincident.get('bbox_separated_pairs'),
        'incident_statuses': [r['status'] for r in incident], 'self_status': self_report['status'],
        'witness_count': len(witnesses), 'witness_pairs': [w['finding'] for w in witnesses]}))


if __name__ == '__main__':
    main()
