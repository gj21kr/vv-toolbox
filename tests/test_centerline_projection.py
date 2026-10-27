import numpy as np
import pytest
import trimesh
from vv_toolbox.centerline_projection import project_outside_stations
from vv_toolbox.centerline_projection import refine_projected_path


def test_bounded_correction_keeps_fixed_points_and_source():
    mesh=trimesh.creation.box(extents=[4,4,4]);vertices=mesh.vertices.copy()
    points=np.array([[2.1,0,0],[1,0,0],[0,0,0]],float);before=points.copy()
    moved,meta=project_outside_stations(mesh,points,movable_indices=[0],inset_mm=.1,max_displacement_mm=.3)
    assert meta['containment']['status']=='PASS' and meta['moved_indices']==[0]
    np.testing.assert_allclose(moved[0],[1.9,0,0]);np.testing.assert_array_equal(moved[1:],points[1:])
    np.testing.assert_array_equal(points,before);np.testing.assert_array_equal(mesh.vertices,vertices)


def test_fixed_outside_endpoint_is_not_silently_moved():
    with pytest.raises(ValueError,match='fixed station'):
        project_outside_stations(trimesh.creation.box(),[[.6,0,0],[0,0,0]],
            movable_indices=[1],inset_mm=.05,max_displacement_mm=.2)


def test_limit_is_not_relaxed_for_failed_projection():
    with pytest.raises(ValueError,match='displacement limit'):
        project_outside_stations(trimesh.creation.box(),[[.8,0,0],[0,0,0]],
            movable_indices=[0],inset_mm=.05,max_displacement_mm=.1)


def test_refinement_routes_concave_corner_without_moving_fixed_endpoints():
    a=trimesh.creation.box(extents=[2.5,1,1]);a.apply_translation([.75,0,0])
    b=trimesh.creation.box(extents=[1,2.5,1]);b.apply_translation([0,.75,0])
    mesh=trimesh.boolean.union([a,b],engine='manifold')
    points=np.array([[1.5,0,0],[0,1.5,0]])
    candidate,meta=refine_projected_path(mesh,points,movable_indices=np.array([],dtype=int),
        inset_mm=.1,max_displacement_mm=.8)
    assert len(candidate)>2 and meta['containment']['status']=='PASS'
    np.testing.assert_array_equal(candidate[[0,-1]],points)
    assert np.all(np.diff(meta['source_parameters'])>0)
    assert meta['maximum_displacement_mm']<=.8


def test_adaptive_inset_does_not_cross_opposite_wall_of_thin_surface():
    mesh=trimesh.creation.box(extents=[1,1,.02])
    points=np.array([[0,0,.02],[.2,0,0]])
    candidate,meta=project_outside_stations(mesh,points,movable_indices=[0,1],
        inset_mm=.05,max_displacement_mm=.1,adaptive_inset=True)
    assert mesh.contains(candidate).all() and meta['containment']['status']=='PASS'
    assert meta['adaptive_inset']
