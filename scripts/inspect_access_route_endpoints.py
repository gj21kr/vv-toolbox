"""Inventory every declared route-slot endpoint without selecting connections."""
import hashlib
from itertools import combinations, product
import json
import math
from pathlib import Path

from vv_toolbox.case_contract import validate_case
from vv_toolbox.case_io import case_digest


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def build_report(case, coverage):
    incidence = validate_case(case)
    if case['model_kind'] != 'source':
        raise ValueError('source case required')
    sources = {s['id']: s['sha256'] for s in case['sources']}
    if (sources.get('bp3d') != coverage['source_sha256'] or
            sources.get('bp3d-preview') != coverage['preview_sha256']):
        raise ValueError('source identities disagree with coverage inspection')
    slots, endpoints = {}, {}
    case_edges = {e['id']: e for e in case['edges']}
    for role, slot in sorted(coverage['route_slots'].items()):
        records = []
        for edge_id in slot['edge_ids']:
            edge = case_edges[edge_id]
            if edge.get('source_part_id') != slot['part_id']:
                raise ValueError('edge part identity mismatch: ' + edge_id)
            for endpoint, index, neighbour in [('start', 0, 1), ('end', -1, -2)]:
                ident = edge_id + ':' + endpoint
                node_id = edge[endpoint]
                points = edge['centerline_mm']
                tangent, position, radius = None, None, None
                if points is not None:
                    position = points[index]
                    radius = edge['radii_mm'][index]
                    if edge['start'] != edge['end']:
                        delta = [a-b for a, b in zip(position, points[neighbour])]
                        norm = math.sqrt(sum(x*x for x in delta))
                        tangent = [x/norm for x in delta]
                row = {'id': ident, 'edge_id': edge_id, 'endpoint': endpoint,
                       'node_id': node_id, 'position_mm': position, 'radius_mm': radius,
                       'outward_unit_tangent': tangent,
                       'tangent_method': 'last source polyline segment, not smoothed anatomical tangent',
                       'tangent_status': 'AVAILABLE' if tangent is not None else 'UNAVAILABLE',
                       'node_incident_edge_ids': sorted(set(incidence[node_id])),
                       'node_kind': case['nodes'][node_id]['kind'],
                       'node_evidence_status': case['nodes'][node_id]['evidence_status'],
                       'edge_evidence_status': edge['evidence_status'],
                       'geometry_kind': edge['geometry_kind'],
                       'identity_refs': edge.get('identity_refs', []),
                       'derivation': edge.get('derivation', {})}
                records.append(row)
                endpoints[ident] = row
        slots[role] = {'part_id': slot['part_id'], 'source_name': slot['source_name'],
                       'obj_sha256': slot['obj_sha256'], 'side_from_name': slot['side_from_name'],
                       'edge_ids': slot['edge_ids'], 'endpoints': records}
    # Include every cross-role combination. No adjacency whitelist, nearest-only
    # pruning, distance threshold, or candidate-to-graph conversion is applied.
    role_pairs, count = [], 0
    for left, right in combinations(sorted(slots), 2):
        pairs = []
        for a, b in product(slots[left]['endpoints'], slots[right]['endpoints']):
            p, q = a['position_mm'], b['position_mm']
            distance, heading_a, heading_b = None, None, None
            if p is not None and q is not None:
                delta = [y-x for x, y in zip(p, q)]
                distance = math.sqrt(sum(x*x for x in delta))
                if distance > 0:
                    direction = [x/distance for x in delta]
                    if a['outward_unit_tangent'] is not None:
                        heading_a = sum(x*y for x, y in zip(a['outward_unit_tangent'], direction))
                    if b['outward_unit_tangent'] is not None:
                        heading_b = -sum(x*y for x, y in zip(b['outward_unit_tangent'], direction))
            pairs.append({'from_endpoint_id': a['id'], 'to_endpoint_id': b['id'],
                          'distance_mm': distance,
                          'from_tangent_toward_other_cosine': heading_a,
                          'to_tangent_toward_other_cosine': heading_b,
                          'shared_source_node': a['node_id'] == b['node_id'],
                          'connection_status': 'UNADJUDICATED'})
        role_pairs.append({'roles': [left, right], 'endpoint_pairs': pairs})
        count += len(pairs)
    return {'schema': 'vv-toolbox.access-route-endpoint-inspection/1',
            'status': 'PASS', 'scope': 'complete declared source-slot endpoint inventory only',
            'source_case_canonical_sha256': case_digest(case),
            'source_sha256': coverage['source_sha256'], 'preview_sha256': coverage['preview_sha256'],
            'frame': case['frame'], 'role_count': len(slots),
            'unique_edge_count': len({e for s in slots.values() for e in s['edge_ids']}),
            'endpoint_count': len(endpoints), 'role_pair_count': len(role_pairs),
            'endpoint_pair_count': count,
            'anatomical_connections': 'UNKNOWN', 'selected_bridges': [],
            'four_access_routes': 'NOT RUN', 'slots': slots, 'role_pairs': role_pairs}


def main():
    root = Path(__file__).resolve().parents[1]
    coverage_path = root / 'docs/evidence/arterial-coverage.json'
    case_path = root / 'exports/atlas-case-inspection/all-arterial-case.json'
    preview_path = root / 'reference-data/bodyparts3d/centerlines-preview.json'
    coverage_raw, case_raw = coverage_path.read_bytes(), case_path.read_bytes()
    coverage = json.loads(coverage_raw)
    if digest(case_raw) != coverage['case_sha256']:
        raise ValueError('case bytes changed since arterial coverage inspection')
    if digest(preview_path.read_bytes()) != coverage['preview_sha256']:
        raise ValueError('preview bytes changed since arterial coverage inspection')
    case = json.loads(case_raw)
    report = build_report(case, coverage)
    report.update(source_case_file_sha256=digest(case_raw), coverage_file_sha256=digest(coverage_raw))
    report['input_bytes_unchanged'] = (coverage_path.read_bytes() == coverage_raw and
                                       case_path.read_bytes() == case_raw)
    if not report['input_bytes_unchanged']:
        raise ValueError('source input changed during inspection')
    target = root / 'docs/evidence/access-route-endpoints.json'
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('slots', 'role_pairs', 'frame')}))


if __name__ == '__main__':
    main()
