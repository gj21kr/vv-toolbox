"""Evidence-bearing case contract, separate from proximity and illustrative graphs."""
import math
import re


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _point(value):
    return (isinstance(value, list) and len(value) == 3 and
            all(type(x) in (int, float) and math.isfinite(x) for x in value))


def validate_case(case):
    """Validate structure/geometry consistency, never anatomical correctness."""
    _require(isinstance(case, dict), 'case must be an object')
    _require(case.get('schema') == 'vv-toolbox.case/1', 'unsupported case schema')
    for key in ('case_id', 'base_model_id'):
        _require(_text(case.get(key)), f'{key} required')
    _require(case.get('model_kind') in ('source', 'synthetic'), 'invalid model kind')
    _require(case.get('split') in ('unassigned', 'train', 'validation', 'test'), 'invalid split')
    frame = case.get('frame')
    _require(isinstance(frame, dict) and _text(frame.get('id')) and _text(frame.get('origin'))
             and frame.get('units') == 'mm' and frame.get('axes') == 'LPS', 'explicit mm/LPS frame required')
    sources = case.get('sources')
    _require(isinstance(sources, list) and len(sources) > 0, 'sources required')
    source_ids = set()
    for source in sources:
        _require(isinstance(source, dict) and _text(source.get('id')), 'invalid source')
        _require(source['id'] not in source_ids, 'duplicate source ID')
        source_ids.add(source['id'])
        _require(isinstance(source.get('sha256'), str) and
                 re.fullmatch('[0-9a-fA-F]{64}', source['sha256']) is not None, 'source SHA256 required')
        _require(_text(source.get('license_ref')), 'source license reference required')
    generation = case.get('generation')
    if case['model_kind'] == 'source':
        _require('generation' in case and generation is None, 'source cannot have generation parameters')
    else:
        _require(isinstance(generation, dict) and type(generation.get('seed')) is int
                 and 0 <= generation['seed'] < 2**64 and _text(generation.get('generator_version'))
                 and isinstance(generation.get('config'), dict), 'synthetic generation contract required')
    nodes, edges = case.get('nodes'), case.get('edges')
    _require(isinstance(nodes, dict) and bool(nodes), 'nodes required')
    _require(isinstance(edges, list) and bool(edges), 'edges required')
    states = ('source_annotation', 'landmark_reviewed', 'synthetic_estimate', 'unresolved')
    for ident, node in nodes.items():
        _require(_text(ident) and isinstance(node, dict), 'invalid node')
        _require(node.get('kind') in ('junction', 'segment_boundary', 'scope_boundary',
                 'anatomical_terminal', 'unresolved'), 'invalid node kind')
        _require(node.get('evidence_status') in states, 'invalid node evidence')
        _require('position_mm' in node, 'node position field required')
        p = node['position_mm']
        _require(_point(p) or (p is None and node['evidence_status'] == 'unresolved'), 'invalid node position')
        _require(case['model_kind'] != 'source' or node['evidence_status'] != 'synthetic_estimate',
                 'synthetic node in source model')
    seen = set()
    incidence = {ident: [] for ident in nodes}
    for edge in edges:
        _require(isinstance(edge, dict) and _text(edge.get('id')), 'edge ID required')
        _require(edge['id'] not in seen, 'duplicate edge ID')
        seen.add(edge['id'])
        start, end = edge.get('start'), edge.get('end')
        _require(isinstance(start, str) and isinstance(end, str) and start in nodes
                 and end in nodes, 'invalid edge endpoints')
        anatomy = edge.get('anatomy')
        _require(isinstance(anatomy, dict) and _text(anatomy.get('artery'))
                 and anatomy.get('side') in ('L', 'R', 'midline', 'unknown')
                 and _text(anatomy.get('segment')) and _text(anatomy.get('branch_id')), 'anatomy fields required')
        refs = edge.get('source_ids')
        _require(isinstance(refs, list) and bool(refs) and
                 all(isinstance(ref, str) and ref in source_ids for ref in refs), 'unknown edge source')
        kind, state = edge.get('geometry_kind'), edge.get('evidence_status')
        _require(kind in ('source', 'estimated') and state in states, 'invalid edge provenance')
        _require((kind == 'estimated') == (state == 'synthetic_estimate'), 'estimated status mismatch')
        _require(case['model_kind'] != 'source' or kind == 'source', 'estimated geometry in source model')
        _require('centerline_mm' in edge and 'radii_mm' in edge, 'geometry fields required')
        points, radii = edge['centerline_mm'], edge['radii_mm']
        if points is None:
            _require(radii is None and state == 'unresolved', 'missing geometry must remain unresolved')
        else:
            _require(isinstance(points, list) and len(points) >= 2 and all(_point(p) for p in points), 'invalid centerline')
            if start == end:
                _require(len(points) >= 4 and len({tuple(p) for p in points}) >= 3,
                         'self loop needs at least three distinct geometry points')
            _require(isinstance(radii, list) and len(radii) == len(points) and
                     all(type(r) in (int, float) and math.isfinite(r) and r > 0 for r in radii), 'invalid radii')
            _require(points[0] == nodes[start]['position_mm'] and points[-1] == nodes[end]['position_mm'],
                     'centerline must share exact junction coordinates')
            _require(all(a != b for a, b in zip(points, points[1:])), 'duplicate consecutive points')
        incidence[start].append(edge['id'])
        incidence[end].append(edge['id'])
    _require(all(incidence.values()), 'orphan node')
    if 'surface_parts' in case:
        from .case_source_surfaces import validate_surface_parts
        validate_surface_parts(case)
    return incidence


def validate_collection(cases):
    """Reject split leakage by declared ancestry and referenced source content.

    Shared archive hashes conservatively bind cases to one split; distinct
    hashes do not prove independent anatomy or independent subjects.
    """
    ids, splits, source_splits = set(), {}, {}
    for case in cases:
        validate_case(case)
        _require(case['case_id'] not in ids, 'duplicate case ID')
        ids.add(case['case_id'])
        base, split = case['base_model_id'], case['split']
        if base in splits:
            _require(splits[base] == split, 'base anatomy assigned to different splits')
        splits[base] = split
        referenced = {ref for edge in case['edges'] for ref in edge['source_ids']}
        for source in case['sources']:
            if source['id'] not in referenced:
                continue
            fingerprint = source['sha256'].lower()
            if fingerprint in source_splits:
                _require(source_splits[fingerprint] == split,
                         'shared geometry source assigned to different splits')
            source_splits[fingerprint] = split
    return {'case_count': len(ids), 'base_model_count': len(splits)}
