from copy import deepcopy

import pytest

from vv_toolbox.case_io import case_digest
from vv_toolbox.trunk_simplification import simplify_synthetic_trunk
from vv_toolbox.route_roles import resolve_source_roles
from test_junction_regularization import fixture as joined_fixture


def fixture():
    case = joined_fixture()
    case['edges'][1]['anatomy'] = deepcopy(case['edges'][0]['anatomy'])
    case['edges'][1]['radii_mm'][0] = case['edges'][0]['radii_mm'][-1]
    twig = deepcopy(case['edges'][0])
    twig.update(id='twig', start='joined', end='tip', centerline_mm=[[10, 0, 0], [10, .5, 0]], radii_mm=[1., 1.])
    case['edges'].append(twig)
    case['nodes']['tip'] = dict(kind='unresolved', evidence_status='unresolved', position_mm=[10, .5, 0])
    spec = dict(schema='vv-toolbox.synthetic-trunk-simplification/1', parent_case_sha256=case_digest(case),
        source_hashes={s['id']: s['sha256'] for s in case['sources']}, trunk_edge_ids=['a', 'b'], omit_edge_id='twig',
        merged_edge_id='trunk', max_omitted_length_mm=1., rationale='explicit synthetic fixture omission', evidence_refs=['fixture'])
    return case, spec


def test_contraction_archives_omission_and_preserves_trunk_points():
    case, spec = fixture(); before = deepcopy(case)
    result = simplify_synthetic_trunk(case, spec, case_id='simplified')
    edge = result['edges'][0]
    assert edge['centerline_mm'] == case['edges'][0]['centerline_mm']+case['edges'][1]['centerline_mm'][1:]
    assert result['synthetic_trunk_simplifications'][0]['original_edges'] == case['edges']
    assert case == before
    with pytest.raises(ValueError, match='missing active descendant'):
        resolve_source_roles(result, {'role': ['a', 'b', 'twig']})
    assert resolve_source_roles(result, {'role': ['a', 'b', 'twig']}, allow_declared_omissions=True) == {'role': ['trunk']}
    with pytest.raises(ValueError, match='entire required role'):
        resolve_source_roles(result, {'role': ['twig']}, allow_declared_omissions=True)


@pytest.mark.parametrize('change', ['length', 'hash', 'radii', 'source', 'branch'])
def test_unsafe_omission_rejected_atomically(change):
    case, spec = fixture()
    if change == 'length': spec['max_omitted_length_mm'] = .1
    if change == 'radii': case['edges'][1]['radii_mm'][0] += .1
    if change == 'source': case['edges'][1]['anatomy']['side'] = 'R' if case['edges'][0]['anatomy']['side'] != 'R' else 'L'
    if change == 'branch':
        edge = deepcopy(case['edges'][-1]); edge['id'] = 'another'; case['edges'].append(edge)
    spec['parent_case_sha256'] = case_digest(case)
    if change == 'hash': spec['parent_case_sha256'] = '0'*64
    before = deepcopy(case)
    with pytest.raises(ValueError): simplify_synthetic_trunk(case, spec, case_id='bad')
    assert case == before
