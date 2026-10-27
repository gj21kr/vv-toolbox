"""Import explicitly mapped source medial paths without inventing junctions."""
from copy import deepcopy

from .case_contract import validate_case


def build_atlas_case(preview, bindings, *, source, extraction_source, frame,
                     case_id, base_model_id, allow_estimated=False):
    """Bindings map source part IDs to explicit artery/side identity candidates.

    Segment boundaries are intentionally not inferred from names. All imported
    geometry and nodes remain unresolved anatomically. Inter-part candidate
    links are retained outside traversable edges. Inputs are never modified.
    """
    if preview.get('schema') != 'vv-toolbox.atlas-centerlines/1':
        raise ValueError('unsupported preview schema')
    if frame.get('confirmed') is not True:
        raise ValueError('independently confirmed source frame required')
    if not isinstance(bindings, dict) or not bindings:
        raise ValueError('explicit part bindings required')
    parts = {p['id']: p for p in preview['parts']}
    if len(parts) != len(preview['parts']):
        raise ValueError('duplicate preview part ID')
    raw_nodes = {n['id']: n for n in preview['nodes']}
    if len(raw_nodes) != len(preview['nodes']):
        raise ValueError('duplicate preview node ID')
    for ident, binding in bindings.items():
        if ident not in parts or parts[ident].get('layer') != 'arterial':
            raise ValueError('binding must reference an arterial source part')
        if not isinstance(binding, dict) or not binding.get('identity_refs'):
            raise ValueError('part identity evidence references required')
    nodes, edges, missing, rejected = {}, [], [], []
    for raw in preview['edges']:
        part_id = raw['part_id']
        if part_id not in bindings:
            continue
        estimated = raw.get('provenance') == 'authored-estimated' and allow_estimated
        if raw.get('provenance') != 'source-mesh-voxel-medial' and not estimated:
            raise ValueError('only source-derived medial paths admitted')
        if raw['start'] == raw['end'] and (len(raw['points']) < 4 or
                len({tuple(p) for p in raw['points']}) < 3):
            rejected.append({'edge_id': raw['id'], 'part_id': part_id,
                             'reason': 'degenerate_self_loop', 'original_edge': deepcopy(raw)})
            continue
        for node_id in (raw['start'], raw['end']):
            if node_id not in raw_nodes or raw_nodes[node_id]['part_id'] != part_id:
                raise ValueError('cross-part or missing extraction endpoint')
            n = raw_nodes[node_id]
            nodes[node_id] = {'kind': 'unresolved', 'evidence_status': 'synthetic_estimate' if estimated else 'unresolved',
                              'position_mm': deepcopy(n['point']),
                              'source_part_id': part_id, 'extraction_kind': n['kind']}
        binding = bindings[part_id]
        edges.append({'id': raw['id'], 'start': raw['start'], 'end': raw['end'],
                      'anatomy': {'artery': binding.get('artery'), 'side': binding.get('side'),
                                  'segment': 'unresolved', 'branch_id': raw['id']},
                      'identity_refs': deepcopy(binding['identity_refs']),
                      'source_part_id': part_id, 'source_ids': [source['id'], extraction_source['id']],
                      'geometry_kind': 'estimated' if estimated else 'source',
                      'evidence_status': 'synthetic_estimate' if estimated else 'unresolved',
                      'centerline_mm': deepcopy(raw['points']), 'radii_mm': deepcopy(raw['radii']),
                      'derivation': {'algorithm': 'authored-estimated' if estimated else preview['algorithm'], 'pitch_mm': raw.get('pitch'),
                                     'radius_status': 'authored_estimate' if estimated else 'voxel_estimate',
                                     'branch_identity_status': 'extraction_edge_not_anatomical_branch'}})
    represented = {e['source_part_id'] for e in edges}
    missing = sorted(set(bindings) - represented)
    if not edges:
        raise ValueError('no mapped source paths available')
    case = {'schema': 'vv-toolbox.case/1', 'case_id': case_id, 'base_model_id': base_model_id,
            'model_kind': 'source', 'split': 'unassigned', 'generation': None,
            'sources': [deepcopy(source), deepcopy(extraction_source)],
            'frame': {key: deepcopy(frame[key]) for key in ('id', 'units', 'axes', 'origin')},
            'nodes': nodes, 'edges': edges,
            'inspection': {'missing_path_parts': missing,
                           'rejected_extraction_edges': rejected,
                           'candidate_links': [deepcopy(link) for link in preview.get('links', [])
                                               if link.get('part_a') in bindings or link.get('part_b') in bindings],
                           'original_units_declaration': preview.get('units'),
                           'segment_materialization': 'NOT RUN'}}
    estimated_ids = [e['id'] for e in edges if e['geometry_kind']=='estimated']
    if estimated_ids:
        case['model_kind'] = 'synthetic'
        case['generation'] = dict(seed=0, generator_version='atlas-source-and-estimates-v1',
                                  config=dict(estimated_edges=estimated_ids,
                                              topology='Independent source endpoints; no inferred cross-part connections'))
    validate_case(case)
    return case
