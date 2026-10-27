"""Explicit coalescence of coincident nodes in a separate synthetic case."""
from copy import deepcopy

from .case_contract import validate_case
from .case_io import case_digest


def coalesce_synthetic_nodes(case, specification, *, case_id):
    """Merge declared identical-position nodes; never move or nearest-snap geometry."""
    validate_case(case)
    spec = specification
    revision = case_digest(case)
    if not isinstance(spec, dict) or spec.get('schema') != 'vv-toolbox.synthetic-node-coalescence/1':
        raise ValueError('unsupported node coalescence specification')
    if spec.get('parent_case_sha256') != revision or spec.get('source_hashes') != {s['id']: s['sha256'] for s in case['sources']}:
        raise ValueError('case and source hashes must match')
    if not isinstance(case_id, str) or not case_id.strip() or case_id == case['case_id']:
        raise ValueError('distinct synthetic case ID required')
    ids, new_id = spec.get('node_ids'), spec.get('node_id')
    if (not isinstance(ids, list) or len(ids) < 2 or
            not all(isinstance(n, str) and n in case['nodes'] for n in ids) or len(set(ids)) != len(ids)):
        raise ValueError('at least two unique existing nodes required')
    if not isinstance(new_id, str) or not new_id.strip() or new_id in case['nodes']:
        raise ValueError('unique new node ID required')
    refs = spec.get('evidence_refs')
    if (not isinstance(refs, list) or not refs or not all(isinstance(r, str) and r.strip() for r in refs)
            or not isinstance(spec.get('rationale'), str) or not spec['rationale'].strip()):
        raise ValueError('explicit evidence and rationale required')
    position = case['nodes'][ids[0]]['position_mm']
    if any(case['nodes'][n]['position_mm'] != position for n in ids[1:]):
        raise ValueError('coalescence requires exactly coincident node positions')
    if any(e['start'] in ids and e['end'] in ids for e in case['edges']):
        raise ValueError('coalescence would collapse an edge into a loop')
    if any(not any(n in (e['start'], e['end']) for e in case['edges']) for n in ids):
        raise ValueError('isolated node cannot define an attachment')
    result = deepcopy(case)
    result['case_id'], result['model_kind'] = case_id, 'synthetic'
    result['generation'] = dict(seed=case['generation']['seed'] if case['generation'] else 0,
        generator_version='explicit-node-coalescence-1', config=dict(specification=deepcopy(spec), parent_generation=deepcopy(case['generation'])))
    changed = []
    for edge in result['edges']:
        if edge['start'] in ids or edge['end'] in ids:
            changed.append(deepcopy(edge))
            for endpoint in ('start', 'end'):
                if edge[endpoint] in ids:
                    edge[endpoint] = new_id
            edge['evidence_status'] = 'synthetic_estimate'
            edge['geometry_kind'] = 'estimated'
            edge['node_coalescence'] = dict(parent_case_revision=revision, source_node_ids=deepcopy(ids),
                                            centerline_and_radii_preserved=True)
    for n in ids:
        result['nodes'].pop(n)
    result['nodes'][new_id] = dict(kind='junction', evidence_status='synthetic_estimate',
        position_mm=deepcopy(position), source_node_ids=deepcopy(ids), evidence_refs=deepcopy(refs), anatomical_junction='UNKNOWN')
    archived = {key: result.pop(key) for key in ('quality', 'geometry_quality', 'surface_quality', 'access_route_inspection', 'route_inspection') if key in result}
    if 'synthetic_route_inspection' in result:
        result['synthetic_route_inspection'].update(source_nodes_preserved=False, source_edges_preserved=False,
            collision_check='NOT RUN', surface_junction_check='NOT RUN', anatomical_connectivity='UNKNOWN')
    for key in ('synthetic_junctions', 'centerline_regularization', 'radius_regularization'):
        if key in result:
            result[key]['geometry_quality'] = 'NOT RUN'
    history = result.setdefault('synthetic_node_coalescences', [])
    history.append(dict(parent_case_revision=revision, specification=deepcopy(spec),
        original_nodes={n: deepcopy(case['nodes'][n]) for n in ids}, original_edges=changed,
        parent_quality_not_applicable=archived))
    validate_case(result)
    return result
