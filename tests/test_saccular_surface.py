from copy import deepcopy
import json

import numpy as np
import pytest
import trimesh

from test_lesions import inputs
from test_saccular_spec import parameters
from vv_toolbox.saccular import saccular_spec
from vv_toolbox.saccular_surface import build_saccular_candidate, _sac_field, _measure_dome
from vv_toolbox.voxel_output import Grid, Surface, voxelize
from vv_toolbox.case_cli import main
from vv_toolbox.case_io import save_case


@pytest.fixture(scope='module')
def candidate():
    case, _ = inputs()
    spec = saccular_spec(case, **parameters())
    before = deepcopy(case)
    vertices, faces, report = build_saccular_candidate(case, spec, spacing_mm=.15)
    assert case == before
    return vertices, faces, report


def test_connected_mesh_and_independent_surface_voxel_lumen(candidate):
    v, f, report = candidate
    mesh = trimesh.Trimesh(vertices=v, faces=f, process=False)
    assert mesh.is_volume and len(mesh.split()) == 1
    # Cross-section intersects the output triangles, not the generator field.
    section = mesh.section(plane_origin=[10,0,0], plane_normal=[1,0,0])
    assert section is not None and len(section.discrete) == 1
    # Independent ray/parity voxelizer checks the parent-neck-sac central channel.
    grid = Grid((3,29,3), (.25,.25,.25), (9.75,-.25,-.25), 'fixture')
    volume = voxelize([Surface(1,0,'estimated',v,f,'fixture','test sac union')], grid)
    assert np.all(volume.foreground[1,1:27,1])
    assert v[:,1].max() == pytest.approx(7, abs=.3)
    neck = mesh.section(plane_origin=[10,2,0], plane_normal=[0,1,0])
    assert neck is not None and len(neck.discrete) == 1
    np.testing.assert_allclose(np.ptp(neck.discrete[0],axis=0)[[0,2]], [2,1], atol=.30, rtol=0)
    assert report['checks']['sampled_lumen_connectivity'] == 'PASS'
    assert report['checks']['neck_dimensions'] == 'PASS'
    assert report['checks']['dome_dimensions']=='PASS'
    np.testing.assert_allclose(report['dome_measurement']['measured_width_depth_height_mm'],
                               [4,3,5],atol=.30,rtol=0)
    assert report['status'] == 'CANDIDATE'
    assert report['generator_version']=='saccular-sidewall-6'
    assert report['specification']['parameters']['dome_width_mm']==4


@pytest.mark.parametrize('change, spacing, budget, error', [
    ({'neck_center_mm':[10,20,0]}, .15, 2_000_000, 'parent wall'),
    ({'outward_normal':[1,0,0], 'width_direction':[0,1,0]}, .15, 2_000_000, 'parent wall'),
    ({}, .3, 2_000_000, 'three cells'),
    ({}, .15, 10, 'budget'),
    ({}, float('nan'), 2_000_000, 'spacing'),
    ({'neck_depth_mm':3}, .15, 2_000_000, 'buried'),
])
def test_invalid_attachment_resolution_and_budget(change, spacing, budget, error):
    case, _ = inputs()
    spec = saccular_spec(case, **dict(parameters(), **change))
    with pytest.raises(ValueError, match=error):
        build_saccular_candidate(case, spec, spacing_mm=spacing, max_grid_voxels=budget)


def test_nearby_unrelated_vessel_blocks_generation():
    case, _ = inputs()
    edge = deepcopy(case['edges'][0])
    edge.update(id='other',start='c',end='d',centerline_mm=[[0,7,0],[20,7,0]])
    for n, position in [('c',[0,7,0]),('d',[20,7,0])]:
        case['nodes'][n] = dict(case['nodes']['a'],position_mm=position)
    case['edges'].append(edge)
    spec = saccular_spec(case, **parameters())
    with pytest.raises(ValueError, match='context clearance'):
        build_saccular_candidate(case, spec, spacing_mm=.15)


def test_returning_parent_blocks_sac_before_surface_generation():
    case, _ = inputs()
    points = [[0,0,0],[20,0,0],[30,0,0],[30,7,0],[10,7,0]]
    case['edges'][0]['centerline_mm'] = points
    case['edges'][0]['radii_mm'] = [2]*len(points)
    case['nodes']['b']['position_mm'] = points[-1]
    spec = saccular_spec(case, **parameters())
    before = deepcopy(case)
    with pytest.raises(ValueError, match='remote parent clearance'):
        build_saccular_candidate(case, spec, spacing_mm=.15)
    assert case == before


def test_neck_rim_inside_baseline_parent_fails_before_grid_allocation():
    case,_ = inputs()
    points=[[0,0,0],[20,0,0],[20,1,0],[10,1,0]]
    case['edges'][0]['centerline_mm']=points
    case['edges'][0]['radii_mm']=[2]*len(points)
    case['nodes']['b']['position_mm']=points[-1]
    spec=saccular_spec(case,**parameters())
    before=deepcopy(case)
    with pytest.raises(ValueError,match='neck rim intersects baseline'):
        build_saccular_candidate(case,spec,spacing_mm=.15,max_grid_voxels=10)
    assert case==before


def test_remote_screen_is_sampling_independent_and_records_exclusion():
    from vv_toolbox.saccular_surface import _remote_parent_clearance
    reports = []
    for xs in ([0,40], list(range(41))):
        points = np.array([[x,0,0] for x in xs],dtype=float)
        index, fraction = (0,.25) if len(xs)==2 else (10,0.)
        reports.append(_remote_parent_clearance(
            points,np.full(len(points),2.),index,fraction,np.array([10,4,0]),4.,.15))
    assert all(r['status']=='PASS' for r in reports)
    assert reports[0]['excluded_station_range_mm']==reports[1]['excluded_station_range_mm']
    minima = [min(i['clearance_lower_bound_mm'] for i in r['intervals']) for r in reports]
    assert minima[0]==pytest.approx(minima[1])


def test_neck_grid_is_rigid_transform_invariant_and_contains_tapered_parent():
    from vv_toolbox.saccular_surface import _neck_grid_bounds
    case,_ = inputs()
    spec = saccular_spec(case,**parameters())
    points = np.array([[0.,0,0],[8,1,2],[20,0,0]])
    radii = np.array([2.,1.,3.])
    low,high = _neck_grid_bounds(points,radii,spec['neck'],spec['parameters'],.15)
    basis = np.column_stack([spec['neck'][key] for key in ('width_axis','depth_axis','normal')])
    for i in range(2):
        for t in np.linspace(0,1,31):
            center = (points[i]+t*(points[i+1]-points[i])-spec['neck']['center_mm'])@basis
            radius = radii[i]+t*(radii[i+1]-radii[i])
            assert np.all(center-radius>low) and np.all(center+radius<high)
    angle=.67
    rotation=np.array([[np.cos(angle),-np.sin(angle),0],
                       [np.sin(angle),np.cos(angle),0],[0,0,1]])
    offset=np.array([200.,-300.,40.])
    neck=deepcopy(spec['neck'])
    neck['center_mm']=(rotation@neck['center_mm']+offset).tolist()
    for key in ('width_axis','depth_axis','normal'):
        neck[key]=(rotation@neck[key]).tolist()
    moved = _neck_grid_bounds(points@rotation.T+offset,radii,neck,spec['parameters'],.15)
    np.testing.assert_allclose(moved,[low,high],atol=1e-10,rtol=0)


def test_sac_profile_derivative_matches_across_neck_plane():
    case, _ = inputs()
    spec = saccular_spec(case, **parameters())
    epsilon = 1e-6
    values = _sac_field(np.array([[11,2-epsilon,0],[11,2,0],[11,2+epsilon,0]]), spec)
    assert (values[1]-values[0])/epsilon == pytest.approx((values[2]-values[1])/epsilon, abs=1e-4)


@pytest.mark.parametrize('angle', [0., .67])
def test_rotated_frame_and_cli_archive(tmp_path, capsys, angle):
    case, _ = inputs()
    # Rotate x into z and translate; no axis-specific parent-wall assumptions.
    rotation = np.array([[0,0,-1],[0,1,0],[1,0,0]])
    rotation = np.array([[np.cos(angle),-np.sin(angle),0],
                         [np.sin(angle),np.cos(angle),0],[0,0,1]]) @ rotation
    offset = np.array([30,-20,50])
    for node in case['nodes'].values():
        node['position_mm'] = (rotation @ node['position_mm']+offset).tolist()
    case['edges'][0]['centerline_mm'] = [(rotation @ np.array(p)+offset).tolist()
                                         for p in case['edges'][0]['centerline_mm']]
    p = parameters()
    p['neck_center_mm'] = (rotation @ p['neck_center_mm']+offset).tolist()
    for key in ('outward_normal', 'width_direction'):
        p[key] = (rotation @ p[key]).tolist()
    spec = saccular_spec(case, **p)
    source, design, output = (tmp_path/n for n in ('case.json','spec.json','sac.npz'))
    save_case(source, case)
    design.write_text(json.dumps(spec))
    assert main(['saccular-surface', str(source), str(design), str(output),
                 '--spacing-mm', '.15']) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'CANDIDATE'
    with np.load(output, allow_pickle=False) as archive:
        meta = json.loads(str(archive['metadata']))
        assert meta['case_revision'] == spec['case_revision']
        local = (archive['vertices_mm']-offset) @ rotation
        assert local[:,1].max() == pytest.approx(7, abs=.3)
        assert meta['checks']['remote_parent_self_contact'] == 'NOT RUN'
        assert meta['neck_measurement']['status'] == 'PASS'
        np.testing.assert_allclose(meta['dome_measurement']['measured_width_depth_height_mm'],
                                   [4,3,5],atol=.30,rtol=0)


def test_finer_grid_keeps_original_neck_target():
    case, _ = inputs()
    spec = saccular_spec(case, **parameters())
    v, f, meta = build_saccular_candidate(case, spec, spacing_mm=.1, max_grid_voxels=5_000_000)
    np.testing.assert_allclose(meta['neck_measurement']['measured_width_depth_mm'],
                               [2,1], atol=.20, rtol=0)
    assert trimesh.Trimesh(vertices=v, faces=f, process=False).is_volume
    np.testing.assert_allclose(meta['dome_measurement']['measured_width_depth_height_mm'],
                               [4,3,5],atol=.20,rtol=0)


def test_dome_measurement_clips_crossing_triangles_and_excludes_tangent_parent():
    # An oblique-sided box crosses the plane. Its clipping intersections have
    # greater x extent than the retained positive vertices alone.
    vertices=np.array([[-4,-1,-1],[4,-1,-1],[4,1,-1],[-4,1,-1],
                       [-2,-1,3],[2,-1,3],[2,1,3],[-2,1,3]])
    faces=np.array([[0,1,5],[0,5,4],[1,2,6],[1,6,5],
                    [2,3,7],[2,7,6],[3,0,4],[3,4,7],
                    [4,5,6],[4,6,7],[0,2,1],[0,3,2]])
    neck=dict(center_mm=[0,0,0],width_axis=[1,0,0],depth_axis=[0,1,0],normal=[0,0,1])
    # Disconnected tangent sheet must not increase the measured dome width.
    vertices=np.vstack([vertices,[[100,0,0],[110,0,0],[100,10,0]]])
    faces=np.vstack([faces,[[8,9,10]]])
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    np.testing.assert_allclose(_measure_dome(mesh,neck),[7,2,3])


@pytest.mark.parametrize('dimensions',[(3.,2.,2.5),(6.,4.,5.)])
def test_different_dome_shapes_keep_requested_dimensions(dimensions):
    case,_=inputs()
    width,depth,height=dimensions
    spec=saccular_spec(case,**dict(parameters(),dome_width_mm=width,
                                  dome_depth_mm=depth,height_perpendicular_mm=height))
    _,_,report=build_saccular_candidate(case,spec,spacing_mm=.15)
    np.testing.assert_allclose(report['dome_measurement']['measured_width_depth_height_mm'],
                               dimensions,atol=.30,rtol=0)
    assert report['specification']==spec


def test_distorted_dome_cannot_pass_with_only_a_correct_neck(monkeypatch):
    from vv_toolbox import saccular_surface
    original=saccular_surface._sac_field
    def enlarged_field(world,spec):
        distorted=deepcopy(spec)
        distorted['parameters']['dome_width_mm']*=2
        return original(world,distorted)
    monkeypatch.setattr(saccular_surface,'_sac_field',enlarged_field)
    case,_=inputs()
    spec=saccular_spec(case,**parameters())
    with pytest.raises(ValueError,match='generated dome dimensions'):
        build_saccular_candidate(case,spec,spacing_mm=.15)
