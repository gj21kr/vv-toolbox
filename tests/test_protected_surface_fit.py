import numpy as np
import pytest
import trimesh

from vv_toolbox.protected_surface_fit import fit_protected_surface


def test_projection_preserves_protected_cap_and_source_topology():
    source=trimesh.creation.cylinder(radius=1,height=6,sections=24)
    target=trimesh.creation.cylinder(radius=.9,height=6,sections=24)
    before=source.vertices.copy()
    fixed=np.flatnonzero(source.vertices[:,2]<-2).tolist()
    result,report=fit_protected_surface(source,target,fixed,max_displacement_mm=.2,transition_rings=1)
    assert np.array_equal(source.vertices,before)
    assert np.array_equal(result.vertices[fixed],before[fixed])
    assert np.array_equal(result.faces,source.faces)
    assert report['moved_vertices']>0 and report['maximum_displacement_mm']<=.2
    assert result.is_watertight and result.is_winding_consistent


def test_duplicate_positions_share_protection():
    base=trimesh.creation.box()
    vertices=base.triangles.reshape(-1,3)
    source=trimesh.Trimesh(vertices,np.arange(len(vertices)).reshape(-1,3),process=False)
    target=trimesh.creation.box(extents=[.8,.8,.8])
    result,_=fit_protected_surface(source,target,[0],max_displacement_mm=.3,transition_rings=1)
    aliases=np.all(vertices==vertices[0],axis=1)
    assert np.array_equal(result.vertices[aliases],vertices[aliases])


def test_excess_projection_is_rejected():
    source=trimesh.creation.cylinder(radius=1,height=6,sections=24)
    target=trimesh.creation.cylinder(radius=.5,height=6,sections=24)
    fixed=np.flatnonzero(source.vertices[:,2]<-2).tolist()
    with pytest.raises(ValueError,match='bound'):
        fit_protected_surface(source,target,fixed,max_displacement_mm=.01)
