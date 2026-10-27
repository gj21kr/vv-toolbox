from copy import deepcopy
import numpy as np
import pytest
import trimesh

from test_bifurcation_saccular import fixture
from vv_toolbox.bifurcation_saccular import bifurcation_saccular_spec
from vv_toolbox.bifurcation_surface import build_bifurcation_candidate, measure_bifurcation_dimensions


def design():
    case,p=fixture()
    for e in case['edges']:
        point=(np.asarray(e['centerline_mm'][-1])*.4).tolist()
        e['centerline_mm'][-1]=point;case['nodes'][e['end']]['position_mm']=point
    normal=-np.ones(3)/np.sqrt(3)
    p.update(neck_center_mm=(2*normal).tolist(),outward_normal=normal.tolist(),
             width_direction=(np.array([1,-1,0])/np.sqrt(2)).tolist())
    return case,bifurcation_saccular_spec(case,**p)


def test_generated_bifurcation_has_one_closed_lumen_and_preserves_source():
    case,spec=design();before=deepcopy(case)
    vertices,faces,meta=build_bifurcation_candidate(case,spec,spacing_mm=.16)
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    assert mesh.is_volume and len(mesh.split())==1
    assert case==before and meta['edge_ids']==['c','d','e']
    assert not meta['accepted_for_generation']
    assert meta['checks']['sampled_lumen_connectivity']=='PASS'
    assert meta['checks']['neck_dimensions']=='PASS'
    assert meta['checks']['dome_dimensions']=='PASS'
    for name in ('neck','dome'):
        measurement=meta['dimension_measurements'][name]
        assert np.all(np.asarray(measurement['absolute_error_mm'])<=.32)
    assert len(meta['lumen_probe_positions_mm'])==6
    # Independently query the actual triangle mesh at all declared probes.
    assert mesh.contains(np.asarray(meta['lumen_probe_positions_mm'])).all()


def test_budget_and_resolution_are_enforced():
    case,spec=design()
    with pytest.raises(ValueError,match='budget'):
        build_bifurcation_candidate(case,spec,spacing_mm=.16,max_grid_voxels=10)
    with pytest.raises(ValueError,match='Spacing'):
        build_bifurcation_candidate(case,spec,spacing_mm=.2)


def test_invalid_attachment_is_not_meshed():
    case,p=fixture()
    with pytest.raises(ValueError,match='attachment'):
        build_bifurcation_candidate(case,bifurcation_saccular_spec(case,**p),spacing_mm=.16)


def test_reversed_branch_preserves_generated_surface():
    case,spec=design()
    first,faces,_=build_bifurcation_candidate(case,spec,spacing_mm=.16)
    edge=case['edges'][0]
    edge['start'],edge['end']=edge['end'],edge['start']
    edge['centerline_mm'].reverse();edge['radii_mm'].reverse()
    reversed_spec=bifurcation_saccular_spec(case,**spec['parameters'])
    second,other_faces,_=build_bifurcation_candidate(case,reversed_spec,spacing_mm=.16)
    assert np.array_equal(faces,other_faces)
    assert np.allclose(first,second,rtol=0,atol=1e-7)


def test_distorted_triangle_surface_fails_dimension_check():
    case,spec=design()
    vertices,faces,_=build_bifurcation_candidate(case,spec,spacing_mm=.16)
    center=np.asarray(spec['neck']['center_mm']);width=np.asarray(spec['neck']['width_axis'])
    vertices=vertices+((vertices-center)@width)[:,None]*width
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    paths=[(np.asarray(e['centerline_mm']),np.asarray(e['radii_mm'])) for e in case['edges']]
    with pytest.raises(ValueError,match='neck dimensions'):
        measure_bifurcation_dimensions(mesh,spec,paths,spacing_mm=.16)


def test_branch_above_neck_is_not_measured_as_dome():
    case,spec=design()
    vertices,faces,_=build_bifurcation_candidate(case,spec,spacing_mm=.16)
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    paths=[(np.asarray(e['centerline_mm']),np.asarray(e['radii_mm'])) for e in case['edges']]
    center=np.asarray(spec['neck']['center_mm']);normal=np.asarray(spec['neck']['normal'])
    paths.append((np.vstack([center+normal,center+2*normal]),np.array([.2,.2])))
    with pytest.raises(ValueError,match='branch extends above'):
        measure_bifurcation_dimensions(mesh,spec,paths,spacing_mm=.16)


def test_dimension_measurements_are_rigid_transform_invariant():
    case,spec=design()
    vertices,faces,meta=build_bifurcation_candidate(case,spec,spacing_mm=.16)
    rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]]);shift=np.array([4,7,-3])
    transform=lambda points:np.asarray(points)@rotation.T+shift
    altered=deepcopy(spec)
    altered['neck']['center_mm']=transform(spec['neck']['center_mm']).tolist()
    for key in ('normal','width_axis','depth_axis'):
        altered['neck'][key]=(rotation@spec['neck'][key]).tolist()
    mesh=trimesh.Trimesh(vertices=transform(vertices),faces=faces,process=False)
    paths=[(transform(e['centerline_mm']),np.asarray(e['radii_mm'])) for e in case['edges']]
    result=measure_bifurcation_dimensions(mesh,altered,paths,spacing_mm=.16)
    for name in ('neck','dome'):
        assert np.allclose(result[name]['measured_mm'],meta['dimension_measurements'][name]['measured_mm'])
