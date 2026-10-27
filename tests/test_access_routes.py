from copy import deepcopy

import pytest

from vv_toolbox.access_routes import inspect_route


def make_case():
    pairs = [('lf', 'a', 'lf'), ('rf', 'a', 'rf'),
             ('a', 'lc', 'lc'), ('a', 'rc', 'rc'),
             ('lc', 'target', 'lt'), ('rc', 'target', 'rt'),
             ('a', 'target', 'shortcut')]
    positions = {name: [i, 0, 0] for i, name in enumerate(['lf', 'rf', 'a', 'lc', 'rc', 'target'])}
    return {
        'schema': 'vv-toolbox.case/1', 'case_id': 'fixture', 'base_model_id': 'fixture',
        'model_kind': 'source', 'split': 'unassigned', 'generation': None,
        'frame': {'id': 'fixture', 'origin': 'fixture', 'units': 'mm', 'axes': 'LPS'},
        'sources': [{'id': 'fixture', 'sha256': 'a'*64, 'license_ref': 'fixture'}],
        'nodes': {n: {'kind': 'junction', 'position_mm': p, 'evidence_status': 'source_annotation'}
                  for n, p in positions.items()},
        'edges': [{'id': ident, 'start': a, 'end': b, 'source_ids': ['fixture'],
                   'geometry_kind': 'source', 'evidence_status': 'source_annotation',
                   'anatomy': {'artery': 'fixture', 'side': 'midline', 'segment': ident, 'branch_id': ident},
                   'centerline_mm': [positions[a], positions[b]], 'radii_mm': [1, 1]}
                  for a, b, ident in pairs]}


@pytest.mark.parametrize('femoral', ['lf', 'rf'])
@pytest.mark.parametrize('carotid,target', [('lc', 'lt'), ('rc', 'rt')])
def test_four_combinations_force_selected_carotid(femoral, carotid, target):
    case = make_case()
    before = deepcopy(case)
    result = inspect_route(case, femoral, 'target', [femoral, carotid, target])
    assert result['status'] == 'PASS'
    assert result['edges'] == [femoral, carotid, target]
    assert result['scope'] == 'source_graph'
    assert case == before


def test_reverse_traversal_supported():
    assert inspect_route(make_case(), 'target', 'lf', ['lt', 'lc', 'lf'])['status'] == 'PASS'


def test_waypoint_spur_cannot_be_visited_and_retraced():
    result = inspect_route(make_case(), 'lf', 'target', ['rf'])
    assert result['status'] == 'FAIL'


def test_unknown_node_prevents_pass():
    case = make_case()
    case['nodes']['lc']['evidence_status'] = 'unresolved'
    result = inspect_route(case, 'lf', 'target', ['lc'])
    assert result['status'] == 'UNKNOWN'
    assert result['unresolved_edges'] == ['lc', 'lt']


def test_estimates_are_separate_from_source_pass():
    case = make_case()
    case.update(model_kind='synthetic', generation={'seed': 1, 'generator_version': 'fixture', 'config': {}})
    case['edges'][2].update(geometry_kind='estimated', evidence_status='synthetic_estimate')
    result = inspect_route(case, 'lf', 'target', ['lc'])
    assert result['status'] == 'PASS'
    assert result['scope'] == 'synthetic_graph'
    assert result['estimated_edges'] == ['lc']


def test_budget_exhaustion_is_not_disconnection():
    result = inspect_route(make_case(), 'lf', 'target', ['lc'], max_states=1)
    assert result['status'] == 'UNKNOWN'
    assert result['reason'] == 'search_budget_exhausted'


@pytest.mark.parametrize('required', [[], ['missing'], ['lc', 'lc']])
def test_invalid_waypoints_rejected(required):
    with pytest.raises(ValueError):
        inspect_route(make_case(), 'lf', 'target', required)


def test_wrong_waypoint_order_fails():
    assert inspect_route(make_case(), 'lf', 'target', ['lt', 'lc'])['status'] == 'FAIL'
