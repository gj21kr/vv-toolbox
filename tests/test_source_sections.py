import numpy as np
import pytest
import trimesh

from vv_toolbox.source_sections import extract_source_sections


def test_explicit_endpoint_planes_are_measured_without_extrapolation():
    from vv_toolbox.section_radius_profile import section_radius_profile
    mesh=trimesh.creation.box(extents=[2,4,8])
    points=[[.2,0,-1],[.2,0,0],[.2,0,1]]
    result=extract_source_sections(mesh,points,include_endpoints=True)
    assert result['endpoint_sections']=='ATTEMPTED'
    assert result['counts']==dict(MEASURED=3,UNKNOWN=0)
    assert [p['origin_mm'] for p in result['profiles']]==points
    assert section_radius_profile(result,3)['measured_count']==3
    for row in result['profiles']:assert row['area_mm2']==pytest.approx(8)


def test_rectangle_contour_preserves_shape_area_center_and_source():
    mesh=trimesh.creation.box(extents=[2,4,8])
    before=mesh.vertices.copy()
    result=extract_source_sections(mesh,[[.2,0,-1],[.2,0,0],[.2,0,1]])
    profile=result['profiles'][0]
    assert profile['status']=='MEASURED'
    assert profile['area_mm2']==pytest.approx(8)
    assert profile['area_equivalent_radius_mm']==pytest.approx(np.sqrt(8/np.pi))
    assert profile['center_boundary_distance_mm']==pytest.approx(.8)
    assert profile['centroid_xyz_mm']==pytest.approx([0,0,0])
    assert np.array_equal(mesh.vertices,before)
    xyz=np.array(profile['contour_xyz_mm'])
    assert xyz[0]==pytest.approx(xyz[-1])
    assert np.max(np.abs(xyz[:,0]))==pytest.approx(1)
    assert np.max(np.abs(xyz[:,1]))==pytest.approx(2)


def test_outside_axis_and_zero_chord_are_unknown():
    mesh=trimesh.creation.box()
    for points in ([[2,0,-.1],[2,0,0],[2,0,.1]],[[0,0,0],[.1,0,0],[0,0,0]]):
        result=extract_source_sections(mesh,points)
        assert result['counts']==dict(MEASURED=0,UNKNOWN=1)


def test_nested_enclosing_contours_are_not_silently_chosen():
    mesh=trimesh.util.concatenate([
        trimesh.creation.box(extents=[4,4,8]),trimesh.creation.box(extents=[2,2,6])])
    row=extract_source_sections(mesh,[[0,0,-1],[0,0,0],[0,0,1]])['profiles'][0]
    assert row['status']=='UNKNOWN' and row['enclosing_contour_count']==2


def test_rigid_transform_preserves_area_and_reconstructs_world_contour():
    mesh=trimesh.creation.box(extents=[2,4,8])
    transform=trimesh.transformations.rotation_matrix(.43,[1,2,3])
    transform[:3,3]=[10,-20,30]
    mesh.apply_transform(transform)
    points=trimesh.transform_points([[0,0,-1],[0,0,0],[0,0,1]],transform)
    row=extract_source_sections(mesh,points)['profiles'][0]
    assert row['area_mm2']==pytest.approx(8)
    assert row['centroid_xyz_mm']==pytest.approx(transform[:3,3])
    _,distance,_=trimesh.proximity.closest_point(mesh,np.array(row['contour_xyz_mm']))
    assert max(distance)<1e-10


def test_physical_window_stabilizes_short_step_tangent_without_moving_stations():
    mesh=trimesh.creation.box(extents=[2,4,10])
    points=[[0,0,-3],[0,0,-.1],[0,0,0],[.1,0,.1],[0,0,3]]
    local=extract_source_sections(mesh,points)['profiles'][1]
    result=extract_source_sections(mesh,points,tangent_half_window_mm=2)
    window=result['profiles'][1]
    assert window['origin_mm']==local['origin_mm']==[0,0,0]
    assert abs(window['normal'][0])<abs(local['normal'][0])/10
    assert result['tangent_half_window_mm']==2
    assert window['status']=='MEASURED'


@pytest.mark.parametrize('window',[0,-1,float('nan'),True])
def test_invalid_physical_window_rejected(window):
    with pytest.raises(ValueError):
        extract_source_sections(trimesh.creation.box(),[[0,0,-.1],[0,0,0],[0,0,.1]],
                                tangent_half_window_mm=window)
