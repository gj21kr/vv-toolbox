"""Explicit, source-preserving terminal-spur omission and trunk contraction."""
from copy import deepcopy
import math

from .case_contract import validate_case
from .case_io import case_digest


def simplify_synthetic_trunk(case, spec, *, case_id):
    validate_case(case)
    revision = case_digest(case)
    if case['model_kind'] != 'synthetic' or not isinstance(spec, dict) or spec.get('schema') != 'vv-toolbox.synthetic-trunk-simplification/1':
        raise ValueError('explicit synthetic trunk specification required')
    if spec.get('parent_case_sha256') != revision or spec.get('source_hashes') != {s['id']: s['sha256'] for s in case['sources']}:
        raise ValueError('case and source hashes must match')
    if not isinstance(case_id, str) or not case_id.strip() or case_id == case['case_id']:
        raise ValueError('distinct synthetic case ID required')
    edges = {e['id']: e for e in case['edges']}
    trunk, spur, new_id = spec.get('trunk_edge_ids'), spec.get('omit_edge_id'), spec.get('merged_edge_id')
    if (not isinstance(trunk, list) or len(trunk) != 2 or not all(isinstance(i, str) and i in edges for i in trunk)
            or len(set(trunk)) != 2 or not isinstance(spur, str) or spur not in edges or spur in trunk):
        raise ValueError('two trunk edges and a distinct omitted edge required')
    if not isinstance(new_id, str) or not new_id.strip() or new_id in edges:
        raise ValueError('unique merged edge ID required')
    selected = trunk+[spur]
    if set(selected) & set(case.get('synthetic_route_inspection', {}).get('bridge_ids', [])):
        raise ValueError('declared bridges cannot be simplified')
    if any(l['edge_id'] in selected for l in case.get('lesions', [])):
        raise ValueError('lesion-bearing paths cannot be simplified')
    refs = spec.get('evidence_refs')
    if not isinstance(refs, list) or not refs or not all(isinstance(r, str) and r.strip() for r in refs) or not isinstance(spec.get('rationale'), str) or not spec['rationale'].strip():
        raise ValueError('explicit omission rationale and evidence required')
    limit = spec.get('max_omitted_length_mm')
    if type(limit) not in (int, float) or not math.isfinite(limit) or limit <= 0:
        raise ValueError('positive finite omission length limit required')
    a, b, twig = [edges[i] for i in selected]
    if any(e['centerline_mm'] is None or e['start'] == e['end'] for e in (a, b, twig)):
        raise ValueError('open paths required')
    shared = {a['start'], a['end']} & {b['start'], b['end']} & {twig['start'], twig['end']}
    if len(shared) != 1:
        raise ValueError('exactly one shared hub required')
    hub = next(iter(shared)); leaf = twig['end'] if twig['start'] == hub else twig['start']
    incident = lambda node: [e['id'] for e in case['edges'] if node in (e['start'], e['end'])]
    if set(incident(hub)) != set(selected) or incident(leaf) != [spur]:
        raise ValueError('only an isolated terminal twig at a three-edge hub may be omitted')
    length = sum(math.dist(p, q) for p, q in zip(twig['centerline_mm'][:-1], twig['centerline_mm'][1:]))
    if length > limit:
        raise ValueError('omitted path exceeds declared length limit')
    keys = ('artery', 'side', 'segment')
    if any(a['anatomy'][k] != b['anatomy'][k] for k in keys) or a['source_ids'] != b['source_ids']:
        raise ValueError('trunk anatomy and source identities must agree')
    reverse_a, reverse_b = a['start'] == hub, b['end'] == hub
    pa = deepcopy(a['centerline_mm'][::-1] if reverse_a else a['centerline_mm'])
    pb = deepcopy(b['centerline_mm'][::-1] if reverse_b else b['centerline_mm'])
    ra = deepcopy(a['radii_mm'][::-1] if reverse_a else a['radii_mm'])
    rb = deepcopy(b['radii_mm'][::-1] if reverse_b else b['radii_mm'])
    if pa[-1] != pb[0] or ra[-1] != rb[0]:
        raise ValueError('shared trunk station must match exactly')
    merged = deepcopy(a)
    merged.update(id=new_id, start=a['end'] if reverse_a else a['start'], end=b['start'] if reverse_b else b['end'],
                  centerline_mm=pa+pb[1:], radii_mm=ra+rb[1:], geometry_kind='estimated', evidence_status='synthetic_estimate')
    merged['anatomy']['branch_id'] = new_id
    merged.pop('derived_interval', None)
    merged['merged_parent_edge_ids'] = list(trunk)
    result = deepcopy(case)
    result['edges'] = [e for e in result['edges'] if e['id'] not in selected]+[merged]
    for e in result['edges']:
        for anchor in e.get('derivation', {}).get('anchors', []):
            if anchor.get('edge_id') not in selected: continue
            old = edges[anchor['edge_id']]
            endpoint = anchor.get('endpoint')
            if endpoint not in ('start', 'end') or old[endpoint] in (hub, leaf):
                raise ValueError('cannot discard a referenced attachment')
            anchor.update(edge_id=new_id, endpoint='start' if old[endpoint] == merged['start'] else 'end')
    result['nodes'].pop(hub); result['nodes'].pop(leaf)
    result.update(case_id=case_id, generation=dict(seed=case['generation']['seed'], generator_version='explicit-trunk-simplification-1',
                  config=dict(specification=deepcopy(spec), parent_generation=deepcopy(case['generation']))))
    archived = {k: result.pop(k) for k in ('quality', 'geometry_quality', 'surface_quality', 'route_inspection', 'access_route_inspection') if k in result}
    result.setdefault('synthetic_trunk_simplifications', []).append(dict(parent_case_revision=revision,
        specification=deepcopy(spec), original_edges=[deepcopy(edges[i]) for i in selected],
        original_nodes={n: deepcopy(case['nodes'][n]) for n in (hub, leaf)}, omitted_edge_id=spur,
        omitted_length_mm=length, parent_quality_not_applicable=archived, anatomical_acceptance='UNKNOWN'))
    if 'synthetic_route_inspection' in result:
        result['synthetic_route_inspection'].update(source_nodes_preserved=False, source_edges_preserved=False,
            collision_check='NOT RUN', surface_junction_check='NOT RUN', anatomical_connectivity='UNKNOWN')
    for key in ('synthetic_junctions', 'centerline_regularization', 'radius_regularization'):
        if key in result: result[key]['geometry_quality'] = 'NOT RUN'
    validate_case(result)
    return result
