import numpy as np
import pytest
import trimesh

from vv_toolbox.radius_sections import inspect_radius_sections


def test_normal_sections_distinguish_inside_and_outside_radii_without_editing():
    mesh=trimesh.creation.box(extents=[2,2,8])
    original=mesh.vertices.copy()
    points=[[0,0,-2],[0,0,0],[0,0,2]]
    assert inspect_radius_sections(mesh,points,[.5]*3)['status']=='PASS'
    result=inspect_radius_sections(mesh,points,[1.5]*3)
    assert result['status']=='FAIL'
    assert result['rows'][0]['outside_samples']==64
    assert result['continuous_tube_wall']=='NOT RUN'
    assert np.array_equal(mesh.vertices,original)


def test_tangent_samples_and_open_surface_are_unknown():
    mesh=trimesh.creation.box(extents=[2,2,8])
    points=[[0,0,-2],[0,0,0],[0,0,2]]
    result=inspect_radius_sections(mesh,points,[1]*3)
    assert result['status']=='UNKNOWN'
    assert result['rows'][0]['ambiguous_samples']==4
    mesh.update_faces(np.arange(len(mesh.faces)-1))
    assert inspect_radius_sections(mesh,points,[.5]*3)['status']=='UNKNOWN'


def test_zero_chord_is_not_silently_skipped():
    result=inspect_radius_sections(trimesh.creation.box(),
                                  [[0,0,0],[.1,0,0],[0,0,0]],[.1]*3)
    assert result['status']=='UNKNOWN' and len(result['rows'])==1


def test_rigid_coordinate_change_preserves_circular_profile_classification():
    mesh=trimesh.creation.box(extents=[2,2,8])
    points=np.array([[0,0,-2],[0,0,0],[0,0,2]],dtype=float)
    transform=trimesh.transformations.rotation_matrix(.73,[1,2,3])
    transform[:3,3]=[123,-45,67]
    mesh.apply_transform(transform)
    transformed=trimesh.transform_points(points,transform)
    assert inspect_radius_sections(mesh,transformed,[.5]*3)['status']=='PASS'
    assert inspect_radius_sections(mesh,transformed,[1.5]*3)['status']=='FAIL'


@pytest.mark.parametrize('radii',[[1],[-1]*3,[float('nan')]*3])
def test_invalid_radii_rejected(radii):
    with pytest.raises(ValueError):
        inspect_radius_sections(trimesh.creation.box(),[[0,0,-.1],[0,0,0],[0,0,.1]],radii)
