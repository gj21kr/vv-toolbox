from copy import deepcopy

import numpy as np
import pytest

from vv_toolbox.centerline_regularization import smooth_synthetic_centerlines
from vv_toolbox.synthetic_routes import build_synthetic_routes
from test_synthetic_routes import fixture


def base():
    source, spec = fixture()
    case = build_synthetic_routes(source, spec, case_id='synthetic')
    edge = case['edges'][-1]
    edge['centerline_mm'] = [[10+i*.1, .12*(-1)**i if 1 < i < 99 else 0., 0.] for i in range(101)]
    edge['radii_mm'] = [2+i*.01 for i in range(101)]
    return case


def apply(case, **changes):
    params = dict(sigma_mm=.5, sample_spacing_mm=.1, max_displacement_mm=.3, case_id='smoothed')
    params.update(changes)
    return smooth_synthetic_centerlines(case, ['bridge'], **params)


def test_filter_reduces_interior_noise_preserves_chords_radii_and_input():
    case = base(); before = deepcopy(case)
    case['quality'] = {'status': 'PASS'}
    before = deepcopy(case)
    result = apply(case)
    old = np.array(case['edges'][-1]['centerline_mm'])
    new = np.array(result['edges'][-1]['centerline_mm'])
    assert np.std(new[25:75, 1]) < .1*np.std(old[25:75, 1])
    np.testing.assert_array_equal(new[[0, 1, -2, -1]], old[[0, 1, -2, -1]])
    assert result['edges'][-1]['radii_mm'] == case['edges'][-1]['radii_mm']
    assert result['edges'][:2] == case['edges'][:2]
    assert result['nodes'] == case['nodes']
    assert result['synthetic_route_inspection']['collision_check'] == 'NOT RUN'
    assert 'quality' not in result
    assert result['centerline_regularization']['parent_quality_not_applicable']['quality']['status'] == 'PASS'
    assert case == before
    assert apply(case) == result


def test_rejects_displacement_without_mutation():
    case = base(); before = deepcopy(case)
    with pytest.raises(ValueError, match='bound'):
        apply(case, max_displacement_mm=.01)
    assert case == before


def test_prior_node_changes_are_not_reported_as_original_nodes():
    case = base()
    case['synthetic_route_inspection']['source_nodes_preserved'] = False
    assert apply(case)['synthetic_route_inspection']['source_nodes_preserved'] is False


def test_straight_path_remains_collinear():
    case = base()
    case['edges'][-1]['centerline_mm'] = [[10+i*.1, 0., 0.] for i in range(101)]
    result = apply(case)
    assert np.max(np.abs(np.asarray(result['edges'][-1]['centerline_mm'])[:, 1:])) == 0


@pytest.mark.parametrize('changes', [dict(sigma_mm=0), dict(sigma_mm=True),
    dict(sample_spacing_mm=float('nan')), dict(max_displacement_mm=-1),
    dict(sample_spacing_mm=.3), dict(case_id='synthetic'), dict(case_id='')])
def test_invalid_parameters(changes):
    with pytest.raises(ValueError): apply(base(), **changes)


def test_source_case_and_short_edges_rejected():
    source, spec = fixture()
    with pytest.raises(ValueError, match='synthetic'):
        smooth_synthetic_centerlines(source, ['a'], sigma_mm=1, sample_spacing_mm=.2,
                                     max_displacement_mm=1, case_id='new')
    case = build_synthetic_routes(source, spec, case_id='synthetic')
    with pytest.raises(ValueError, match='five'):
        smooth_synthetic_centerlines(case, ['a'], sigma_mm=1, sample_spacing_mm=.2,
                                     max_displacement_mm=1, case_id='new')


def test_selected_lesion_rejected_other_lesion_preserved():
    case = base(); case['lesions'] = [{'edge_id': 'bridge'}]
    with pytest.raises(ValueError, match='lesion'): apply(case)
    case['lesions'] = [{'edge_id': 'a'}]
    assert apply(case)['lesions'] == case['lesions']


def test_grid_budget_fails_before_large_allocation():
    with pytest.raises(ValueError, match='budget'):
        apply(base(), sample_spacing_mm=1e-8)


def test_reversal_equivariance():
    case = base(); reverse = deepcopy(case)
    edge = reverse['edges'][-1]
    edge['start'], edge['end'] = edge['end'], edge['start']
    edge['centerline_mm'].reverse(); edge['radii_mm'].reverse()
    a = apply(case)['edges'][-1]['centerline_mm']
    b = apply(reverse)['edges'][-1]['centerline_mm'][::-1]
    np.testing.assert_allclose(a, b, atol=1e-12, rtol=0)
