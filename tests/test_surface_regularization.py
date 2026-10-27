import numpy as np
import pytest
import trimesh
from vv_toolbox.surface_regularization import regularize_surface


def test_preserves_connectivity_input_and_rigid_transform():
    mesh=trimesh.creation.icosphere(subdivisions=2,radius=2)
    original=mesh.vertices.copy()
    v,f,report=regularize_surface(original,mesh.faces,iterations=3,
        max_displacement_mm=.2,max_volume_change_fraction=.1)
    np.testing.assert_array_equal(f,mesh.faces)
    np.testing.assert_array_equal(original,mesh.vertices)
    assert report['checks']['closed_surface']=='PASS'
    shifted,_,_=regularize_surface(original+[200,-300,1500],mesh.faces,iterations=3,
        max_displacement_mm=.2,max_volume_change_fraction=.1)
    np.testing.assert_allclose(shifted-[200,-300,1500],v,atol=1e-10)


def test_displacement_failure_leaves_input_unchanged():
    mesh=trimesh.creation.icosphere(subdivisions=1)
    original=mesh.vertices.copy()
    with pytest.raises(ValueError,match='displacement limit'):
        regularize_surface(mesh.vertices,mesh.faces,iterations=10,
            max_displacement_mm=1e-12,max_volume_change_fraction=.1)
    np.testing.assert_array_equal(original,mesh.vertices)


def test_open_input_rejected():
    mesh=trimesh.creation.icosphere(subdivisions=1)
    with pytest.raises(ValueError,match='closed input'):
        regularize_surface(mesh.vertices,mesh.faces[1:],iterations=3,
            max_displacement_mm=.2,max_volume_change_fraction=.1)


def test_volume_limit_is_independent_of_displacement_limit():
    mesh=trimesh.creation.icosphere(subdivisions=1)
    with pytest.raises(ValueError,match='volume preservation'):
        regularize_surface(mesh.vertices,mesh.faces,iterations=3,
            max_displacement_mm=10.,max_volume_change_fraction=1e-12)
