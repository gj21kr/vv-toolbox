from copy import deepcopy

import pytest

from vv_toolbox.case_io import case_digest
from vv_toolbox.synthetic_nodes import coalesce_synthetic_nodes
from test_synthetic_routes import fixture


def request():
    case, _ = fixture()
    case['nodes']['2']['position_mm'] = [10, 0, 0]
    case['edges'][1]['centerline_mm'][0] = [10, 0, 0]
    spec = dict(schema='vv-toolbox.synthetic-node-coalescence/1', parent_case_sha256=case_digest(case),
                source_hashes={s['id']: s['sha256'] for s in case['sources']}, node_ids=['1', '2'],
                node_id='joined', rationale='explicit synthetic fixture', evidence_refs=['fixture'])
    return case, spec


def test_coincident_nodes_merge_without_moving_geometry():
    case, spec = request()
    before = deepcopy(case)
    result = coalesce_synthetic_nodes(case, spec, case_id='joined-case')
    assert case == before
    assert result['edges'][0]['end'] == result['edges'][1]['start'] == 'joined'
    assert all(a['centerline_mm'] == b['centerline_mm'] and a['radii_mm'] == b['radii_mm'] for a, b in zip(case['edges'], result['edges']))
    assert result['synthetic_node_coalescences'][0]['original_edges'] == case['edges']
    assert result['nodes']['joined']['anatomical_junction'] == 'UNKNOWN'


@pytest.mark.parametrize('mutation', ['distance', 'hash', 'duplicate', 'existing', 'evidence'])
def test_invalid_coalescence_does_not_mutate_input(mutation):
    case, spec = request()
    if mutation == 'distance':
        case['nodes']['2']['position_mm'] = [10.001, 0, 0]
        case['edges'][1]['centerline_mm'][0] = [10.001, 0, 0]
        spec['parent_case_sha256'] = case_digest(case)
    if mutation == 'hash': spec['parent_case_sha256'] = '0'*64
    if mutation == 'duplicate': spec['node_ids'] = ['1', '1']
    if mutation == 'existing': spec['node_id'] = '0'
    if mutation == 'evidence': spec['evidence_refs'] = []
    before = deepcopy(case)
    with pytest.raises(ValueError):
        coalesce_synthetic_nodes(case, spec, case_id='bad')
    assert case == before
