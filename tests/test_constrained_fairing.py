import numpy as np
import pytest
import trimesh
from vv_toolbox.constrained_fairing import fair_surface


def test_fixed_vertices_and_translation_equivariance():
    mesh=trimesh.creation.icosphere(subdivisions=1)
    free=np.flatnonzero(mesh.vertices[:,2]>.2)
    before=mesh.vertices.copy()
    moved,report=fair_surface(before,mesh.faces,free,strength=1,
        max_displacement_mm=.5,max_volume_change_fraction=.5)
    fixed=np.setdiff1d(np.arange(len(before)),free)
    assert np.array_equal(moved[fixed],before[fixed])
    assert np.array_equal(mesh.vertices,before)
    shifted,_=fair_surface(before+[100,200,1500],mesh.faces,free,strength=1,
        max_displacement_mm=.5,max_volume_change_fraction=.5)
    assert np.allclose(shifted-[100,200,1500],moved,atol=1e-10)
    assert report['max_displacement_mm']>0


def test_preservation_limit_is_not_relaxed():
    mesh=trimesh.creation.icosphere(subdivisions=1)
    with pytest.raises(ValueError,match='displacement'):
        fair_surface(mesh.vertices,mesh.faces,np.arange(len(mesh.vertices)),strength=10,
            max_displacement_mm=1e-8,max_volume_change_fraction=.5)
