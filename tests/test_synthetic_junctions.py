from copy import deepcopy

import pytest

from vv_toolbox.case_contract import validate_case
from vv_toolbox.case_io import case_digest
from vv_toolbox.synthetic_junctions import split_synthetic_junction
from vv_toolbox.synthetic_routes import build_synthetic_routes
from test_synthetic_routes import fixture


def spec(case):
    return {'schema': 'vv-toolbox.synthetic-junction/1', 'parent_case_sha256': case_digest(case),
        'source_hashes': {s['id']: s['sha256'] for s in case['sources']},
        'edge_id': 'a', 'interval_index': 0, 'fraction': .4, 'node_id': 'new',
        'child_edge_ids': ['a0', 'a1'], 'rationale': 'synthetic prospective attachment',
        'evidence_refs': ['fixture inspection']}


def test_source_preservation_fractional_split_and_lineage():
    case, _ = fixture(); before = deepcopy(case)
    declaration = spec(case)
    result = split_synthetic_junction(case, declaration, case_id='split')
    assert case == before
    assert result['model_kind'] == 'synthetic' and result['generation']['seed'] == 0
    assert result['base_model_id'] == case['base_model_id'] and result['split'] == case['split']
    assert result['sources'] == case['sources']
    assert result['edges'][-1] == case['edges'][-1]
    assert result['nodes']['new']['position_mm'] == [4., 0., 0.]
    a, b = result['edges'][:2]
    assert a['radii_mm'][-1] == b['radii_mm'][0] == 1.4
    assert a['centerline_mm'][-1] == b['centerline_mm'][0]
    assert a['anatomy'] == b['anatomy'] == case['edges'][0]['anatomy']
    assert a['evidence_status'] == b['evidence_status'] == 'synthetic_estimate'
    assert result['synthetic_junctions']['history'][0]['parent_edge'] == case['edges'][0]
    assert set(validate_case(result)['new']) == {'a0', 'a1'}
    assert split_synthetic_junction(case, declaration, case_id='split') == result


def test_existing_sample_split_does_not_duplicate_points():
    case, _ = fixture()
    edge = case['edges'][0]
    edge['centerline_mm'].insert(1, [4., 0., 0.]); edge['radii_mm'].insert(1, 1.4)
    declaration = spec(case)
    del declaration['interval_index'], declaration['fraction']
    declaration['sample_index'] = 1
    result = split_synthetic_junction(case, declaration, case_id='split')
    assert [len(e['centerline_mm']) for e in result['edges'][:2]] == [2, 2]


def test_existing_bridge_outer_anchor_rebound_and_quality_invalidated():
    case, bridge_spec = fixture()
    case = build_synthetic_routes(case, bridge_spec, case_id='synthetic')
    before = deepcopy(case)
    result = split_synthetic_junction(case, spec(case), case_id='split')
    bridge = next(e for e in result['edges'] if e['id'] == 'bridge')
    assert bridge['derivation']['anchors'][0] == {'edge_id': 'a1', 'endpoint': 'end'}
    assert bridge['centerline_mm'] == case['edges'][-1]['centerline_mm']
    assert result['synthetic_route_inspection']['bridge_ids'] == ['bridge']
    assert result['synthetic_route_inspection']['collision_check'] == 'NOT RUN'
    assert result['synthetic_junctions']['history'][0]['bridge_anchor_rebindings'][0]['before']['edge_id'] == 'a'
    assert case == before


@pytest.mark.parametrize('mutation', ['case_hash', 'source_hash', 'fraction0', 'fraction1', 'fraction_nan',
    'interval_bool', 'node_collision', 'child_collision', 'duplicate_children', 'sample_endpoint', 'both_modes', 'no_refs'])
def test_invalid_declarations_do_not_mutate(mutation):
    case, _ = fixture(); before = deepcopy(case); declaration = spec(case)
    if mutation == 'case_hash': declaration['parent_case_sha256'] = 'a'*64
    if mutation == 'source_hash': declaration['source_hashes'] = {}
    if mutation == 'fraction0': declaration['fraction'] = 0
    if mutation == 'fraction1': declaration['fraction'] = 1
    if mutation == 'fraction_nan': declaration['fraction'] = float('nan')
    if mutation == 'interval_bool': declaration['interval_index'] = True
    if mutation == 'node_collision': declaration['node_id'] = '0'
    if mutation == 'child_collision': declaration['child_edge_ids'] = ['a', 'b0']
    if mutation == 'duplicate_children': declaration['child_edge_ids'] = ['x', 'x']
    if mutation == 'sample_endpoint':
        declaration.pop('interval_index'); declaration.pop('fraction'); declaration['sample_index'] = 0
    if mutation == 'both_modes': declaration['sample_index'] = 1
    if mutation == 'no_refs': declaration['evidence_refs'] = []
    with pytest.raises(ValueError): split_synthetic_junction(case, declaration, case_id='split')
    assert case == before


def test_selected_lesion_and_declared_bridge_rejected():
    case, bridges = fixture(); case['lesions'] = [{'edge_id': 'a'}]
    with pytest.raises(ValueError, match='lesion'):
        split_synthetic_junction(case, spec(case), case_id='split')
    case.pop('lesions')
    case = build_synthetic_routes(case, bridges, case_id='synthetic')
    declaration = spec(case); declaration['edge_id'] = 'bridge'
    with pytest.raises(ValueError, match='declared bridge'):
        split_synthetic_junction(case, declaration, case_id='split')


def test_sequential_splits_preserve_parent_archives():
    case, _ = fixture()
    first = split_synthetic_junction(case, spec(case), case_id='first')
    declaration = spec(first); declaration.update(edge_id='a1', node_id='next', child_edge_ids=['a10', 'a11'])
    second = split_synthetic_junction(first, declaration, case_id='second')
    assert len(second['synthetic_junctions']['history']) == 2
    assert second['synthetic_junctions']['history'][0] == first['synthetic_junctions']['history'][0]
