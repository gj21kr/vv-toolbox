import numpy as np
import pytest
import trimesh

from vv_toolbox.source_patch import extract_source_patch
from vv_toolbox.protected_patch_check import check_protected_patch


def fixture():
    mesh=trimesh.creation.box()
    patch=extract_source_patch(mesh.vertices,mesh.faces,[0])
    free=np.setdiff1d(np.arange(len(mesh.vertices)),patch['source_vertex_ids'])
    return mesh,patch,free


def test_bounded_edit_keeps_protected_triangles():
    mesh,patch,free=fixture()
    moved=mesh.vertices.copy();moved[free]*=1.01
    result=check_protected_patch(mesh.vertices,moved,mesh.faces,patch,allowed_vertex_ids=free,max_displacement_mm=.1)
    assert result['status']=='PASS' and result['moved_vertices']==len(free)


def test_fixed_coordinate_change_is_rejected():
    mesh,patch,free=fixture()
    moved=mesh.vertices.copy();moved[patch['source_vertex_ids'][0],0]+=1e-10
    with pytest.raises(ValueError,match='Fixed'):
        check_protected_patch(mesh.vertices,moved,mesh.faces,patch,allowed_vertex_ids=free,max_displacement_mm=.1)


def test_protected_id_cannot_be_declared_free():
    mesh,patch,free=fixture()
    with pytest.raises(ValueError,match='overlaps'):
        check_protected_patch(mesh.vertices,mesh.vertices,mesh.faces,patch,
                              allowed_vertex_ids=np.arange(len(mesh.vertices)),max_displacement_mm=.1)


def test_excessive_displacement_rejected():
    mesh,patch,free=fixture()
    moved=mesh.vertices.copy();moved[free]*=1.5
    with pytest.raises(ValueError,match='bound'):
        check_protected_patch(mesh.vertices,moved,mesh.faces,patch,allowed_vertex_ids=free,max_displacement_mm=.01)
