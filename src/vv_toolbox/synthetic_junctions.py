"""Explicit source-addressed splits for separately authored synthetic junctions."""
from copy import deepcopy
import math

from .case_contract import validate_case
from .case_io import case_digest


def trim_synthetic_terminal(case, specification, *, case_id):
    """Discard an explicitly addressed free terminal tail in a derived case.

    Uses the same immutable split/address contract as junction construction.
    No closest-point inference or anatomical boundary approval is performed.
    """
    validate_case(case)
    spec = specification
    if not isinstance(spec, dict) or spec.get('schema') != 'vv-toolbox.synthetic-terminal-trim/1':
        raise ValueError('unsupported terminal trim specification')
    endpoint = spec.get('remove_endpoint')
    if endpoint not in ('start', 'end'):
        raise ValueError('explicit remove_endpoint required')
    edge = next((e for e in case['edges'] if e['id'] == spec.get('edge_id')), None)
    if edge is None:
        raise ValueError('known parent edge required')
    old_node = edge[endpoint]
    if sum(old_node in (e['start'], e['end']) for e in case['edges']) != 1:
        raise ValueError('only a free terminal endpoint may be trimmed')
    # Reject malformed/nonincident anchor references as well as graph incidence.
    if any(a.get('edge_id') == edge['id'] and a.get('endpoint') == endpoint
           for e in case['edges'] for a in e.get('derivation', {}).get('anchors', [])):
        raise ValueError('cannot trim an endpoint referenced by a bridge')
    split_spec = deepcopy(spec)
    split_spec['schema'] = 'vv-toolbox.synthetic-junction/1'
    split_spec.pop('remove_endpoint')
    result = split_synthetic_junction(case, split_spec, case_id=case_id)
    removed_id = spec['child_edge_ids'][0 if endpoint == 'start' else 1]
    removed = next(e for e in result['edges'] if e['id'] == removed_id)
    result['edges'] = [e for e in result['edges'] if e['id'] != removed_id]
    result['nodes'].pop(old_node)
    node = result['nodes'][spec['node_id']]
    node.update(kind='unresolved', anatomical_junction='UNKNOWN', terminal_trim=True)
    result['generation']['generator_version'] = 'explicit-terminal-trim-1'
    result['generation']['config']['specification'] = deepcopy(spec)
    history = result['synthetic_junctions']['history'][-1]
    history.update(operation='terminal_trim', remove_endpoint=endpoint,
                   removed_tail=deepcopy(removed), removed_node=deepcopy(case['nodes'][old_node]),
                   removed_node_id=old_node)
    if 'synthetic_route_inspection' in result:
        result['synthetic_route_inspection']['source_nodes_preserved'] = False
    validate_case(result)
    return result


def split_synthetic_bridge(case, specification, *, case_id):
    """Split a declared bridge while retaining its external attachment lineage."""
    if not isinstance(specification, dict) or specification.get('schema') != 'vv-toolbox.synthetic-bridge-split/1':
        raise ValueError('unsupported bridge split specification')
    spec = deepcopy(specification)
    spec['schema'] = 'vv-toolbox.synthetic-junction/1'
    result = _split_synthetic_junction(case, spec, case_id=case_id, bridge_split=True)
    result['generation']['generator_version'] = 'explicit-bridge-split-1'
    result['generation']['config']['specification'] = deepcopy(specification)
    return result


def split_synthetic_junction(case, specification, *, case_id):
    return _split_synthetic_junction(case, specification, case_id=case_id)


def _split_synthetic_junction(case, specification, *, case_id, bridge_split=False):
    """Split one addressed open path without asserting anatomical branching.

    The source/synthetic input is immutable. A new node has degree two until
    explicitly connected later; its prospective junction role is synthetic.
    Fractional interval and existing internal sample addressing are exclusive.
    """
    validate_case(case)
    revision = case_digest(case)
    if not isinstance(case_id, str) or not case_id.strip() or case_id == case['case_id']:
        raise ValueError('distinct synthetic case ID required')
    spec = specification
    if not isinstance(spec, dict) or spec.get('schema') != 'vv-toolbox.synthetic-junction/1':
        raise ValueError('unsupported synthetic junction specification')
    if spec.get('parent_case_sha256') != revision:
        raise ValueError('parent case hash mismatch')
    if spec.get('source_hashes') != {s['id']: s['sha256'] for s in case['sources']}:
        raise ValueError('exact source hashes required')
    edges = {edge['id']: edge for edge in case['edges']}
    ident = spec.get('edge_id')
    if not isinstance(ident, str) or ident not in edges:
        raise ValueError('known parent edge required')
    edge = edges[ident]
    declared = ident in case.get('synthetic_route_inspection', {}).get('bridge_ids', [])
    if bridge_split and (case['model_kind'] != 'synthetic' or not declared):
        raise ValueError('declared synthetic bridge required')
    if bridge_split and edge.get('bridge_split'):
        raise ValueError('nested bridge split requires explicit multi-generation lineage support')
    if declared and not bridge_split:
        raise ValueError('splitting a declared bridge requires a separate bridge lineage operation')
    if edge['centerline_mm'] is None or edge['start'] == edge['end']:
        raise ValueError('open parent centerline required')
    if any(lesion['edge_id'] == ident for lesion in case.get('lesions', [])):
        raise ValueError('cannot split an edge carrying a lesion')
    node_id, children = spec.get('node_id'), spec.get('child_edge_ids')
    if not isinstance(node_id, str) or not node_id.strip() or node_id in case['nodes']:
        raise ValueError('unique new node ID required')
    if (not isinstance(children, list) or len(children) != 2 or
            not all(isinstance(i, str) and i.strip() and i not in edges for i in children) or
            children[0] == children[1]):
        raise ValueError('two unique new child edge IDs required')
    refs = spec.get('evidence_refs')
    if (not isinstance(refs, list) or not refs or
            not all(isinstance(r, str) and r.strip() for r in refs) or
            not isinstance(spec.get('rationale'), str) or not spec['rationale'].strip()):
        raise ValueError('explicit rationale and evidence references required')
    points, radii = edge['centerline_mm'], edge['radii_mm']
    if 'sample_index' in spec:
        i = spec['sample_index']
        if 'interval_index' in spec or 'fraction' in spec or type(i) is not int or not 0 < i < len(points)-1:
            raise ValueError('exclusive internal sample index required')
        position, radius, address = deepcopy(points[i]), radii[i], float(i)
        split_points = [deepcopy(points[:i+1]), deepcopy(points[i:])]
        split_radii = [deepcopy(radii[:i+1]), deepcopy(radii[i:])]
    else:
        i, fraction = spec.get('interval_index'), spec.get('fraction')
        if (type(i) is not int or not 0 <= i < len(points)-1 or
                type(fraction) not in (int, float) or not math.isfinite(fraction) or not 0 < fraction < 1):
            raise ValueError('internal fractional interval address required')
        address = i+fraction
        position = [a+fraction*(b-a) for a, b in zip(points[i], points[i+1])]
        radius = radii[i]+fraction*(radii[i+1]-radii[i])
        split_points = [deepcopy(points[:i+1])+[position], [position]+deepcopy(points[i+1:])]
        split_radii = [deepcopy(radii[:i+1])+[radius], [radius]+deepcopy(radii[i+1:])]
    result = deepcopy(case)
    result['case_id'], result['model_kind'] = case_id, 'synthetic'
    result['generation'] = {'seed': case['generation']['seed'] if case['generation'] else 0,
        'generator_version': 'explicit-junction-split-1',
        'config': {'specification': deepcopy(spec), 'parent_case_revision': revision,
                   'parent_generation': deepcopy(case['generation'])}}
    result['nodes'][node_id] = {'kind': 'junction', 'evidence_status': 'synthetic_estimate',
        'position_mm': deepcopy(position), 'source_edge_id': ident,
        'source_interval_address': address, 'evidence_refs': deepcopy(refs),
        'anatomical_junction': 'UNKNOWN'}
    pieces = []
    for index, child_id in enumerate(children):
        child = deepcopy(edge)
        child.update(id=child_id, start=edge['start'] if index == 0 else node_id,
            end=node_id if index == 0 else edge['end'], centerline_mm=deepcopy(split_points[index]),
            radii_mm=deepcopy(split_radii[index]), geometry_kind='estimated', evidence_status='synthetic_estimate')
        child['derived_interval'] = {'parent_case_revision': revision, 'parent_edge_id': ident,
            'start_address': 0. if index == 0 else address,
            'end_address': address if index == 0 else float(len(points)-1),
            'address_units': 'original sample index plus fractional interval',
            'anatomical_segment_assignment': 'NOT CREATED'}
        pieces.append(child)
    if bridge_split:
        anchors = edge.get('derivation', {}).get('anchors')
        if not isinstance(anchors, list) or len(anchors) != 2:
            raise ValueError('bridge must retain two external anchors')
        for index, child in enumerate(pieces):
            sibling = {'edge_id': children[1-index], 'endpoint': 'start' if index == 0 else 'end'}
            child['derivation']['anchors'] = ([deepcopy(anchors[0]), sibling] if index == 0 else
                                               [sibling, deepcopy(anchors[1])])
            child['bridge_split'] = dict(parent_bridge_id=ident, parent_case_revision=revision,
                                        sibling_edge_id=children[1-index], internal_endpoint='end' if index == 0 else 'start')
            if index == 1:
                child['derivation'].pop('from_direction_xyz', None)
                child['derivation'].pop('from_radius_mm', None)
                child['derivation']['attachment_mode'] = 'continuation'
    result['edges'] = [item for original in result['edges'] for item in (pieces if original['id'] == ident else [original])]
    archived = {key: result.pop(key) for key in (
        'synthetic_route_inspection', 'quality', 'geometry_quality', 'surface_quality',
        'access_route_inspection', 'route_inspection') if key in result}
    rebound = []
    for other in result['edges']:
        anchors = other.get('derivation', {}).get('anchors', [])
        for anchor in anchors:
            if anchor.get('edge_id') == ident:
                endpoint = anchor.get('endpoint')
                if endpoint not in ('start', 'end'):
                    raise ValueError('cannot rebind an ambiguous existing bridge anchor')
                old = deepcopy(anchor)
                anchor['edge_id'] = children[0 if endpoint == 'start' else 1]
                rebound.append({'bridge_id': other['id'], 'before': old, 'after': deepcopy(anchor)})
    previous_routes = archived.get('synthetic_route_inspection')
    if previous_routes is not None:
        result['synthetic_route_inspection'] = {
            'bridge_ids': deepcopy(previous_routes['bridge_ids']),
            'source_case_sha256': previous_routes['source_case_sha256'],
            'source_nodes_preserved': previous_routes.get('source_nodes_preserved', False), 'source_edges_preserved': False,
            'collision_check': 'NOT RUN', 'surface_junction_check': 'NOT RUN',
            'anatomical_connectivity': 'UNKNOWN'}
        if bridge_split:
            result['synthetic_route_inspection']['bridge_ids'] = [item
                for old_id in previous_routes['bridge_ids']
                for item in (children if old_id == ident else [old_id])]
    for key in ('centerline_regularization', 'radius_regularization'):
        if key in result:
            result[key]['geometry_quality'] = 'NOT RUN'
    previous_history = deepcopy(result.get('synthetic_junctions', {}).get('history', []))
    previous_history.append({'parent_case_revision': revision, 'parent_edge': deepcopy(edge),
        'source_hashes': deepcopy(spec['source_hashes']), 'node_id': node_id,
        'child_edge_ids': deepcopy(children), 'source_interval_address': address,
        'rationale': spec['rationale'], 'evidence_refs': deepcopy(refs),
        'bridge_anchor_rebindings': rebound,
        'parent_quality_not_applicable': archived})
    result['synthetic_junctions'] = {'history': previous_history, 'geometry_quality': 'NOT RUN',
        'route_checks': 'NOT RUN', 'anatomical_acceptance': 'UNKNOWN'}
    validate_case(result)
    return result
