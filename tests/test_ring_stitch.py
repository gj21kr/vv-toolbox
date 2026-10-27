import numpy as np
import pytest
import trimesh
from vv_toolbox.ring_stitch import stitch_rings
from vv_toolbox.patch_boundary import patch_boundary_loops


@pytest.mark.parametrize('counts',[(8,13),(13,8),(8,8),(38,125)])
def test_strip_preserves_both_original_rings(counts):
    n,m=counts
    a=np.arange(n)*2*np.pi/n
    b=np.arange(m)*2*np.pi/m
    vertices=np.vstack([np.c_[np.cos(a),np.sin(a),np.zeros(n)],
                        np.c_[2*np.cos(b),2*np.sin(b),np.ones(m)]])
    faces=stitch_rings(np.arange(n),a,np.arange(n,n+m),b)
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    assert len(faces)==n+m and mesh.euler_number==0
    assert mesh.is_winding_consistent and np.all(mesh.area_faces>0)
    loops=patch_boundary_loops(faces,np.arange(len(faces)))
    assert {frozenset(loop) for loop in loops}=={
        frozenset(range(n)),frozenset(range(n,n+m))}


def test_closed_caps_produce_one_volume_without_duplicate_boundary_vertices():
    n,m=8,13
    a=np.arange(n)*2*np.pi/n;b=np.arange(m)*2*np.pi/m
    vertices=np.vstack([np.c_[np.cos(a),np.sin(a),np.zeros(n)],
                        np.c_[np.cos(b),np.sin(b),np.ones(m)],
                        [[0,0,0],[0,0,1]]])
    strip=stitch_rings(np.arange(n),a,np.arange(n,n+m),b)
    caps=[[n+m,(i+1)%n,i] for i in range(n)]
    caps += [[n+m+1,n+j,n+(j+1)%m] for j in range(m)]
    mesh=trimesh.Trimesh(vertices=vertices,faces=np.vstack([strip,caps]),process=False)
    assert mesh.is_watertight and mesh.is_winding_consistent
    assert len(mesh.split())==1


def test_ambiguous_parameterization_rejected():
    with pytest.raises(ValueError):
        stitch_rings([0,1,2],[0,2,1],[3,4,5],[0,1,2])
    with pytest.raises(ValueError,match='disjoint'):
        stitch_rings([0,1,2],[0,1,2],[2,3,4],[0,1,2])
