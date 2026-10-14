from copy import deepcopy

import numpy as np
import pytest

from vv_toolbox.atlas_modification import deform_part, validate_parameters
from vv_toolbox.model import tube_mesh


def fixture(curved=True):
    t = np.linspace(0., 1., 101)
    points = np.column_stack((40 * t, 6 * np.sin(np.pi * t) if curved else t * 0, t * 0))
    vertices, faces = tube_mesh(points, 1., sides=16)
    part = dict(id='test', layer='arterial', vertices=vertices, faces=faces)
    edge = dict(id='edge', part_id='test', start='a', end='b', points=points.tolist(), radii=np.ones(len(points)).tolist())
    return part, [edge]


def test_default_is_exact_identity_and_copies_input():
    part, edges = fixture()
    result, paths = deform_part(part, edges, {})
    np.testing.assert_array_equal(result['vertices'], part['vertices'])
    assert paths == edges
    result['vertices'][0] += 1
    assert not np.array_equal(result['vertices'], part['vertices'])


@pytest.mark.parametrize('parameters', [{'radius_scale': 1.5}, {'tortuosity': .6}, {'torsion_deg': 90}])
def test_controls_change_geometry_keep_anchors_and_original(parameters):
    part, edges = fixture()
    original = deepcopy(part)
    original_edges = deepcopy(edges)
    result, paths = deform_part(part, edges, parameters)
    assert np.max(np.linalg.norm(result['vertices'] - part['vertices'], axis=1)) > .1
    np.testing.assert_array_equal(np.asarray(paths[0]['points'])[[0, -1]], np.asarray(edges[0]['points'])[[0, -1]])
    np.testing.assert_array_equal(result['vertices'][:16], part['vertices'][:16])
    np.testing.assert_array_equal(result['vertices'][-16:], part['vertices'][-16:])
    np.testing.assert_array_equal(part['vertices'], original['vertices'])
    np.testing.assert_array_equal(result['faces'], part['faces'])
    assert edges == original_edges
    assert np.isfinite(result['vertices']).all()


def test_radius_scales_middle_and_torsion_moves_out_of_plane():
    part, edges = fixture()
    result, paths = deform_part(part, edges, {'radius_scale': 1.5})
    assert paths[0]['radii'][50] == pytest.approx(1.5)
    _, twisted = deform_part(part, edges, {'torsion_deg': 90})
    assert np.asarray(twisted[0]['points'])[:, 2].max() > 4
    np.testing.assert_allclose(np.asarray(twisted[0]['points'])[:, 0], np.asarray(edges[0]['points'])[:, 0])


def test_straight_path_can_bend_and_negative_tortuosity_reduces_curve():
    part, edges = fixture(False)
    _, bent = deform_part(part, edges, {'tortuosity': 1})
    assert np.max(np.linalg.norm(np.asarray(bent[0]['points']) - edges[0]['points'], axis=1)) > 2
    part, edges = fixture()
    _, straighter = deform_part(part, edges, {'tortuosity': -1})
    assert np.asarray(straighter[0]['points'])[50, 1] == pytest.approx(0, abs=1e-10)


@pytest.mark.parametrize('parameters', [{'radius_scale': 0}, {'torsion_deg': 181}, {'tortuosity': np.nan}, {'radius_scale': True}, {'unknown': 1}, {'torsion_deg': '90'}])
def test_invalid_parameters_rejected(parameters):
    with pytest.raises(ValueError):
        validate_parameters(parameters)


def test_missing_nonfinite_or_wrong_part_paths_rejected():
    part, edges = fixture()
    with pytest.raises(ValueError):
        deform_part(part, [], {})
    edges[0]['points'][1][0] = np.inf
    with pytest.raises(ValueError):
        deform_part(part, edges, {})
    _, edges = fixture()
    edges[0]['part_id'] = 'other'
    with pytest.raises(ValueError):
        deform_part(part, edges, {})


def test_junction_collars_and_smooth_long_branch_displacement():
    part, edges = fixture()
    branch = deepcopy(edges[0])
    branch['id'] = 'branch'
    branch['start'] = 'b'
    branch['end'] = 'c'
    branch['points'] = (np.asarray(branch['points']) + [40, 0, 0]).tolist()
    vertices, faces = tube_mesh(np.asarray(branch['points']), 1., sides=16)
    part['faces'] = np.vstack((part['faces'], faces + len(part['vertices'])))
    part['vertices'] = np.vstack((part['vertices'], vertices))
    edges.append(branch)
    result, paths = deform_part(part, edges, dict(radius_scale=2, tortuosity=1, torsion_deg=180))
    junction = np.array([40, 0, 0])
    collar = np.linalg.norm(part['vertices'] - junction, axis=1) <= 1.5
    assert collar.sum() >= 32
    np.testing.assert_array_equal(result['vertices'][collar], part['vertices'][collar])
    for original, changed in zip(edges, paths):
        shift = np.asarray(changed['points']) - original['points']
        # A smooth field on dense paths, including the fixed-to-moving transition.
        assert np.linalg.norm(np.diff(shift, n=2, axis=0), axis=1).max() < .2
        assert np.linalg.norm(shift, axis=1).max() > 1
        assert np.isfinite(changed['points']).all()
