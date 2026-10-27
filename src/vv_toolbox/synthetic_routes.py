"""Explicit source-endpoint bridges; no nearest-neighbour anatomy inference."""
from copy import deepcopy
import math

from .case_contract import validate_case
from .case_io import case_digest
from .access_routes import inspect_route


def build_synthetic_routes(source, specification, *, case_id):
    return _build_synthetic_routes(source,specification,case_id=case_id,extension=False)


def extend_synthetic_routes(source, specification, *, case_id):
    """Add declared bridges to a hash-bound existing synthetic case."""
    return _build_synthetic_routes(source,specification,case_id=case_id,extension=True)


def _build_synthetic_routes(source, specification, *, case_id, extension):
    """Preserve every source edge/node and append declared Hermite bridges.

    Each anchor names an exact source edge and endpoint. Handles are explicit
    lengths in mm, not fitted anatomy. Endpoint tangents and radii agree with
    the selected source edges. Finite sampling is not a collision/smoothness
    certificate, and unresolved source evidence remains unresolved.
    """
    validate_case(source)
    if source['model_kind'] != ('synthetic' if extension else 'source'):
        raise ValueError('synthetic parent required' if extension else 'immutable source case required')
    if not isinstance(case_id, str) or not case_id.strip() or case_id == source['case_id']:
        raise ValueError('distinct synthetic case ID required')
    schema = 'vv-toolbox.synthetic-route-extension/1' if extension else 'vv-toolbox.synthetic-routes/1'
    if not isinstance(specification, dict) or specification.get('schema') != schema:
        raise ValueError('unsupported route specification')
    if specification.get('parent_case_sha256' if extension else 'source_case_sha256') != case_digest(source):
        raise ValueError('source case hash mismatch')
    bridges = specification.get('bridges')
    if not isinstance(bridges, list) or not bridges:
        raise ValueError('explicit bridge list required')
    original = {e['id']: e for e in source['edges']}
    result = deepcopy(source)
    result.update(case_id=case_id, model_kind='synthetic', generation={
        'seed': 0, 'generator_version': 'explicit-endpoint-hermite-1',
        'config': deepcopy(specification)})
    if extension:
        result['generation'].update(seed=source['generation']['seed'],generator_version='explicit-endpoint-hermite-extension-1')
        result['generation']['config']['parent_generation'] = deepcopy(source['generation'])
    ids = set(original)
    node_pairs = {tuple(sorted((e['start'], e['end']))) for e in source['edges']}

    def anchor(binding):
        if not isinstance(binding, dict) or binding.get('edge_id') not in original:
            raise ValueError('known source edge anchor required')
        edge = original[binding['edge_id']]
        endpoint = binding.get('endpoint')
        if endpoint not in ('start', 'end') or edge['centerline_mm'] is None:
            raise ValueError('source endpoint geometry required')
        if edge['start'] == edge['end']:
            raise ValueError('closed source edge has no outward endpoint tangent')
        points = edge['centerline_mm']
        index, neighbour = (0, 1) if endpoint == 'start' else (-1, -2)
        p, q = points[index], points[neighbour]
        delta = [a - b for a, b in zip(p, q)]
        length = math.sqrt(sum(x*x for x in delta))
        return edge, edge[endpoint], p, [x/length for x in delta], edge['radii_mm'][index]

    for bridge in bridges:
        if not isinstance(bridge, dict):
            raise ValueError('bridge must be an object')
        ident = bridge.get('id')
        if not isinstance(ident, str) or not ident.strip() or ident in ids:
            raise ValueError('unique new bridge ID required')
        ids.add(ident)
        refs = bridge.get('evidence_refs')
        if (not isinstance(refs, list) or not refs or
                not all(isinstance(r, str) and r.strip() for r in refs) or
                not isinstance(bridge.get('rationale'), str) or not bridge['rationale'].strip()):
            raise ValueError('bridge rationale and evidence references required')
        a, na, p, outward_a, ra = anchor(bridge.get('from'))
        b, nb, q, outward_b, rb = anchor(bridge.get('to'))
        mode = bridge.get('attachment_mode','continuation')
        branch_parameters = {}
        if mode == 'side_branch':
            if not extension or sum(na in (e['start'],e['end']) for e in source['edges']) < 2:
                raise ValueError('side branch requires an explicit split junction in a synthetic parent')
            direction, radius = bridge.get('from_direction_xyz'), bridge.get('from_radius_mm')
            if (not isinstance(direction,list) or len(direction)!=3 or
                    not all(type(x) in (int,float) and math.isfinite(x) for x in direction) or
                    type(radius) not in (int,float) or not math.isfinite(radius) or not 0 < radius <= ra):
                raise ValueError('side branch requires finite direction and positive radius no larger than parent')
            norm = math.sqrt(sum(x*x for x in direction))
            if norm <= 1e-12:
                raise ValueError('nonzero branch direction required')
            outward_a, ra = [x/norm for x in direction], radius
            branch_parameters = dict(attachment_mode=mode,from_direction_xyz=outward_a,from_radius_mm=radius)
        elif mode != 'continuation' or 'from_direction_xyz' in bridge or 'from_radius_mm' in bridge:
            raise ValueError('branch overrides require side_branch mode')
        pair = tuple(sorted((na, nb)))
        if na == nb or p == q or pair in node_pairs:
            raise ValueError('distinct, nonduplicate bridge endpoints required')
        node_pairs.add(pair)
        handles = bridge.get('handle_lengths_mm')
        samples = bridge.get('samples')
        if (not isinstance(handles, list) or len(handles) != 2 or
                not all(type(h) in (int, float) and math.isfinite(h) and h > 0 for h in handles)):
            raise ValueError('two positive finite handle lengths required')
        if type(samples) is not int or not 3 <= samples <= 10000:
            raise ValueError('samples must be an integer from 3 to 10000')
        if mode == 'continuation':
            # Test the continuous cubic, not its sampled polyline. Overlapping
            # source tails need explicit trimming, not a backwards gap bridge.
            chord = [y-x for x, y in zip(p, q)]
            length = math.sqrt(sum(x*x for x in chord))
            axis = [x/length for x in chord]
            m0 = handles[0]*sum(x*y for x, y in zip(outward_a, axis))
            m1 = -handles[1]*sum(x*y for x, y in zip(outward_b, axis))
            quadratic = -6*length+3*m0+3*m1
            linear = 6*length-4*m0-2*m1
            values = [m0, m1]
            if quadratic > 0:
                t_min = -linear/(2*quadratic)
                if 0 < t_min < 1:
                    values.append(quadratic*t_min*t_min+linear*t_min+m0)
            if min(values) < -1e-10*max(length, *handles):
                raise ValueError(
                    'continuation reverses along endpoint chord; '
                    'review anchors, trim overlapping tails, or shorten handles')
        points, radii = [], []
        for i in range(samples):
            t = i/(samples-1)
            s = t*t*(3-2*t)
            points.append([(1-s)*p[j] + s*q[j] +
                           (t**3-2*t*t+t)*handles[0]*outward_a[j] -
                           (t**3-t*t)*handles[1]*outward_b[j] for j in range(3)])
            radii.append((1-s)*ra+s*rb)
        points[0], points[-1] = deepcopy(p), deepcopy(q)
        result['edges'].append({
            'id': ident, 'start': na, 'end': nb,
            'anatomy': {'artery': 'synthetic connection', 'side': 'unknown',
                       'segment': 'unresolved', 'branch_id': ident},
            'source_ids': sorted(set(a['source_ids'] + b['source_ids'])),
            'geometry_kind': 'estimated', 'evidence_status': 'synthetic_estimate',
            'centerline_mm': points, 'radii_mm': radii,
            'derivation': {'anchors': deepcopy([bridge['from'], bridge['to']]),
                           **branch_parameters,
                           'evidence_refs': deepcopy(refs), 'rationale': bridge['rationale'],
                           'anatomical_connection': 'UNKNOWN'}})
    validate_case(result)
    result['synthetic_route_inspection'] = {
        'source_case_sha256': case_digest(source),
        'source_edges_preserved': True, 'source_nodes_preserved': True,
        'bridge_ids': [b['id'] for b in bridges],
        'anatomical_connectivity': 'UNKNOWN', 'collision_check': 'NOT RUN',
        'surface_junction_check': 'NOT RUN'}
    if extension:
        previous = source.get('synthetic_route_inspection',{})
        result['synthetic_route_inspection'].update(
            parent_case_sha256=case_digest(source),
            source_case_sha256=previous.get('source_case_sha256'),
            source_edges_preserved=False,
            parent_edges_preserved=True,parent_nodes_preserved=True,
            bridge_ids=list(previous.get('bridge_ids',[]))+[b['id'] for b in bridges])
        archived = {key:result.pop(key) for key in ('quality','geometry_quality','surface_quality') if key in result}
        if archived:
            result['synthetic_route_inspection']['parent_quality_not_applicable'] = archived
        for key in ('radius_regularization','centerline_regularization'):
            if key in result:
                result[key]['geometry_quality'] = 'NOT RUN'
    return result


def inspect_four_access_routes(case, routes):
    """Inspect four explicitly identified L/R femoral and carotid combinations.

    Roles are bound to exact edge IDs and source identity sides; no artery-name
    heuristic chooses an edge. Results describe graph reachability only.
    """
    validate_case(case)
    if not isinstance(routes, list) or len(routes) != 4:
        raise ValueError('exactly four route declarations required')
    edges = {e['id']: e for e in case['edges']}
    seen, reports = set(), []
    for route in routes:
        if not isinstance(route, dict):
            raise ValueError('route declaration must be an object')
        pair = (route.get('femoral_side'), route.get('carotid_side'))
        if pair not in {('L', 'L'), ('L', 'R'), ('R', 'L'), ('R', 'R')} or pair in seen:
            raise ValueError('unique four side combinations required')
        seen.add(pair)
        required = route.get('required_edges')
        for role, side in zip(('femoral_edge', 'carotid_edge'), pair):
            role_id = route.get(role)
            edge = edges.get(role_id) if isinstance(role_id, str) else None
            if (edge is None or edge['anatomy']['side'] != side or
                    not isinstance(required, list) or edge['id'] not in required):
                raise ValueError('explicit side-matching mandatory role edge required')
        if required.index(route['femoral_edge']) >= required.index(route['carotid_edge']):
            raise ValueError('femoral must precede carotid')
        femoral = edges[route['femoral_edge']]
        if (required[0] != femoral['id'] or
                route.get('start') not in (femoral['start'], femoral['end'])):
            raise ValueError('route must start at the declared femoral edge')
        reports.append({'femoral_side': pair[0], 'carotid_side': pair[1],
                        'result': inspect_route(case, route['start'], route['end'], required)})
    return {'scope': 'declared graph routes, not anatomical or catheter validation',
            'anatomical_acceptance': 'UNKNOWN', 'routes': reports}
