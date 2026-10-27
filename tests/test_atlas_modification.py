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


@pytest.mark.parametrize('version', ['v2', 'v3'])
def test_shared_path_points_match_surface_field_probes_and_duplicate_constraints(version):
    part, edges = fixture()
    points = np.asarray(edges[0]['points'])
    original_count = len(part['vertices'])
    part['vertices'] = np.vstack((part['vertices'], points))
    region = dict(center_mm=points[50].tolist(), radius_mm=2., transition_width_mm=8.)
    parameters = dict(radius_scale=1.3, tortuosity=.3, torsion_deg=35)
    result, paths = deform_part(part, edges, parameters, protected_regions=[region],
                               anchor_blend='product', field_version=version)
    np.testing.assert_array_equal(result['vertices'][original_count:], paths[0]['points'])
    duplicated, duplicate_paths = deform_part(
        part, edges, parameters, protected_regions=[region, region],
        anchor_blend='product', field_version=version)
    np.testing.assert_array_equal(result['vertices'], duplicated['vertices'])
    assert paths == duplicate_paths
    np.testing.assert_array_equal(np.asarray(paths[0]['points'])[[0, -1]], points[[0, -1]])
    assert np.linalg.norm(result['vertices'][:original_count] -
                          part['vertices'][:original_count], axis=1).max() > .1
    assert result['modification']['method'].endswith('-' + version)


def test_compact_support_membership_change_is_continuous_and_unsupported_queries_fail():
    from scipy.spatial import cKDTree
    from vv_toolbox.atlas_modification import _compact_field
    samples = np.array([[0., 0, 0], [1., 0, 0]])
    shifts = np.array([[0., 1, 0], [0., -1, 0]])
    tangents = np.array([[1., 0, 0], [1., 0, 0]])
    tree = cKDTree(samples)
    def evaluate(x):
        return _compact_field(np.array([[x, 0., 0.]]), samples, shifts,
                              tangents, np.ones(2), tree, 2.)[0][0]
    # First sample exits support at x=2 while the second still supports queries.
    jumps = [np.linalg.norm(evaluate(2.-h) - evaluate(2.+h)) for h in (.1, .01, .001)]
    assert jumps[1] < jumps[0] * .01
    assert jumps[2] < jumps[1] * .01
    with pytest.raises(ValueError, match='support'):
        evaluate(5.)


def test_v1_remains_default_and_unknown_field_is_rejected():
    part, edges = fixture()
    parameters = dict(radius_scale=1.3, tortuosity=.3, torsion_deg=35)
    default, paths = deform_part(part, edges, parameters)
    explicit, explicit_paths = deform_part(part, edges, parameters, field_version='v1')
    np.testing.assert_array_equal(default['vertices'], explicit['vertices'])
    assert paths == explicit_paths
    with pytest.raises(ValueError, match='field version'):
        deform_part(part, edges, {}, field_version='unknown')


def test_polyline_radius_mode_preserves_curved_centerline_and_changes_surface():
    part, edges = fixture()
    edited, paths = deform_part(part, edges, dict(radius_scale=1.3),
                               field_version='v3', radial_mode='polyline')
    np.testing.assert_array_equal(paths[0]['points'], edges[0]['points'])
    assert np.max(np.linalg.norm(edited['vertices'] - part['vertices'], axis=1)) > .2
    assert max(paths[0]['radii']) > 1.2


def test_polyline_radial_does_not_invent_segments_between_paths():
    from vv_toolbox.atlas_modification import _polyline_radial
    paths = [np.array([[0.,0,0],[1,0,0]]), np.array([[9.,0,0],[10,0,0]])]
    result = _polyline_radial(np.array([[5.,1,0],[.5,1,0]]), paths)
    np.testing.assert_array_equal(result, [[4.,1,0],[0.,1,0]])


def test_stationary_flow_matches_analytic_expansion_and_fixes_zero_velocity():
    from vv_toolbox.atlas_modification import _integrate_field
    points = np.array([[0.,0,0],[1.,2,3]])
    rate = np.log(1.3)
    def field(v):
        return v + rate * v, np.full(len(v), 1. + rate)
    moved, scales = _integrate_field(points, field, 16)
    np.testing.assert_allclose(moved, points * 1.3, atol=1e-8, rtol=0)
    np.testing.assert_allclose(scales, 1.3, atol=1e-14)
    np.testing.assert_array_equal(moved[0], points[0])


@pytest.mark.parametrize('steps', [-1, True, 1.5, 257])
def test_invalid_integration_steps_rejected(steps):
    part, edges = fixture()
    with pytest.raises(ValueError, match='Integration'):
        deform_part(part, edges, {}, field_version='v3', integration_steps=steps)


def test_frozen_support_replays_identical_field():
    part, edges = fixture()
    params = dict(radius_scale=1.3, tortuosity=.3, torsion_deg=35.)
    first, paths = deform_part(part, edges, params, field_version='v3', radial_mode='polyline')
    replay, replay_paths = deform_part(
        part, edges, params, field_version='v3', radial_mode='polyline',
        field_support_mm=first['modification']['field_support_mm'])
    np.testing.assert_array_equal(first['vertices'], replay['vertices'])
    assert paths == replay_paths


@pytest.mark.parametrize('support', [0., -1., float('nan'), float('inf'), True, '3'])
def test_invalid_frozen_support_rejected(support):
    part, edges = fixture()
    with pytest.raises(ValueError, match='field support'):
        deform_part(part, edges, {}, field_version='v3', field_support_mm=support)


def test_explicit_geometric_region_fixes_surface_and_path_with_shared_field():
    part,edges=fixture()
    center=np.asarray(edges[0]['points'][50])
    region=dict(center_mm=center.tolist(),radius_mm=2.)
    result,changed=deform_part(part,edges,dict(radius_scale=1.3,tortuosity=.3,torsion_deg=35),
                               protected_regions=[region])
    fixed=np.linalg.norm(part['vertices']-center,axis=1)<=2.
    assert fixed.any()
    np.testing.assert_array_equal(result['vertices'][fixed],part['vertices'][fixed])
    points=np.asarray(edges[0]['points']);inside=np.linalg.norm(points-center,axis=1)<=2.
    np.testing.assert_array_equal(np.asarray(changed[0]['points'])[inside],points[inside])
    np.testing.assert_array_equal(np.asarray(changed[0]['radii'])[inside],np.asarray(edges[0]['radii'])[inside])
    assert np.linalg.norm(result['vertices']-part['vertices'],axis=1).max()>.1
    assert result['modification']['protected_regions']==[region]
    assert result['modification']['clinical_validation'] is False


@pytest.mark.parametrize('region',[
    dict(center_mm=[0,0],radius_mm=1),
    dict(center_mm=[0,0,0],radius_mm=0),
    dict(center_mm=[0,0,0],radius_mm=True),
    dict(center_mm=[0,float('nan'),0],radius_mm=1)])
def test_invalid_protected_region_rejected(region):
    part,edges=fixture()
    with pytest.raises(ValueError):
        deform_part(part,edges,{},protected_regions=[region])


def test_transition_width_changes_falloff_without_changing_fixed_region():
    from vv_toolbox.atlas_modification import _anchor_weight
    points=np.array([[0.,0,0],[2,0,0],[3,0,0],[6,0,0]])
    original=_anchor_weight(points,[[0,0,0]],[2])
    wider=_anchor_weight(points,[[0,0,0]],[2],[4])
    np.testing.assert_array_equal(wider[:2],[0,0])
    assert 0<wider[2]<original[2]<1
    assert wider[3]==1


@pytest.mark.parametrize('width',[0,-1,float('nan'),True])
def test_invalid_transition_width_rejected(width):
    part,edges=fixture()
    with pytest.raises(ValueError,match='transition width'):
        deform_part(part,edges,{},protected_regions=[
            dict(center_mm=[0,0,0],radius_mm=1,transition_width_mm=width)])


def test_product_anchor_blend_is_bounded_and_smooth_at_equal_weights():
    from vv_toolbox.atlas_modification import _anchor_weight
    step=1e-5
    points=np.column_stack((np.array([3-step,3,3+step]),np.zeros((3,2))))
    values=_anchor_weight(points,[[0,0,0],[6,0,0]],[1,1],[4,4],blend='product')
    assert np.all((values>=0)&(values<=1))
    left=(values[1]-values[0])/step;right=(values[2]-values[1])/step
    assert abs(left-right)<1e-4
    assert values[1]==pytest.approx(.25)
    zero=_anchor_weight(np.array([[0.,0,0],[10,0,0]]),[[0,0,0],[6,0,0]],[1,1],[4,4],blend='product')
    assert zero[0]==0 and zero[1]>0


def test_product_deformation_records_method_and_preserves_protected_surface():
    part,edges=fixture();center=np.asarray(edges[0]['points'][50])
    region=dict(center_mm=center.tolist(),radius_mm=2,transition_width_mm=4)
    result,changed=deform_part(part,edges,dict(tortuosity=.3,torsion_deg=35),
                               protected_regions=[region],anchor_blend='product')
    inside=np.linalg.norm(part['vertices']-center,axis=1)<=2
    np.testing.assert_array_equal(result['vertices'][inside],part['vertices'][inside])
    assert result['modification']['anchor_blend']=='product'
    assert np.linalg.norm(result['vertices']-part['vertices'],axis=1).max()>.1


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
