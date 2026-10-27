from copy import deepcopy

import pytest

from vv_toolbox.case_io import case_digest
from vv_toolbox.synthetic_nodes import coalesce_synthetic_nodes
from vv_toolbox.junction_regularization import smooth_continuation_node
from test_synthetic_nodes import request


def fixture():
    case, spec = request()
    case['edges'][0]['centerline_mm'] = [[0, 0, 0], [5, 0, 0], [9, 0, 0], [10, 0, 0]]
    case['edges'][0]['radii_mm'] = [1., 1., 1., 1.]
    case['edges'][1]['centerline_mm'] = [[10, 0, 0], [11, 1, 0], [20, 1, 0], [30, 0, 0]]
    case['edges'][1]['radii_mm'] = [1.2, 1.2, 1.2, 1.2]
    spec['parent_case_sha256'] = case_digest(case)
    return coalesce_synthetic_nodes(case, spec, case_id='joined-case')


def apply(case, **kwargs):
    return smooth_continuation_node(case, 'joined', sigma_mm=.5, support_mm=2., sample_spacing_mm=.1,
                                    max_displacement_mm=kwargs.get('bound', 1.), max_radius_change_mm=1., case_id='smooth')


def test_joint_smoothing_preserves_outer_chords_and_shared_node():
    case = fixture(); before = deepcopy(case)
    result = apply(case)
    a, b = result['edges']
    assert a['centerline_mm'][-1] == b['centerline_mm'][0] == result['nodes']['joined']['position_mm']
    assert a['radii_mm'][-1] == b['radii_mm'][0]
    assert a['centerline_mm'][:2] == case['edges'][0]['centerline_mm'][:2]
    assert b['centerline_mm'][-2:] == case['edges'][1]['centerline_mm'][-2:]
    assert case == before


def test_bound_rejection_does_not_modify_case():
    case = fixture(); before = deepcopy(case)
    with pytest.raises(ValueError, match='bounds'):
        apply(case, bound=.00001)
    assert case == before


def test_reversed_edge_orientation_is_equivalent():
    case = fixture(); expected = apply(case)
    for e in case['edges']:
        e['start'], e['end'] = e['end'], e['start']
        e['centerline_mm'].reverse(); e['radii_mm'].reverse()
    actual = apply(case)
    for a, b in zip(actual['edges'], expected['edges']):
        assert a['centerline_mm'][::-1] == b['centerline_mm']
        assert a['radii_mm'][::-1] == b['radii_mm']


def test_branch_node_cannot_be_smoothed_as_continuation():
    case = fixture()
    e = deepcopy(case['edges'][0]); e.update(id='third', end='joined')
    case['edges'].append(e)
    with pytest.raises(ValueError, match='degree-two'):
        apply(case)
