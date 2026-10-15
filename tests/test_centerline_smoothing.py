import copy
import numpy as np
from vv_toolbox.atlas_centerlines import smooth_edge


def test_voxel_staircase_smoothing_preserves_anchors_and_bounds():
    x=np.arange(60,dtype=float)
    p=np.column_stack([x,np.floor(x/3),np.zeros(len(x))])
    edge=dict(points=p.tolist(),radii=[3.]*len(p),pitch=1.,provenance='source-mesh-voxel-medial')
    original=copy.deepcopy(edge);out=smooth_edge(edge);q=np.array(out['points'])
    assert edge==original
    np.testing.assert_array_equal(q[[0,-1]],p[[0,-1]])
    assert np.isfinite(q).all()
    def turning(v):
        d=np.diff(v,axis=0);d/=np.linalg.norm(d,axis=1)[:,None]
        return np.linalg.norm(np.diff(d,axis=0),axis=1).max()
    assert turning(q)<turning(p)*.5
    assert out['smoothing']['max_displacement']<=1.05
    assert len(out['radii'])==len(q)


def test_estimated_paths_and_short_edges_are_not_changed():
    edge=dict(points=[[0,0,0],[1,1,0]],radii=[1,1],pitch=1.,provenance='source-mesh-voxel-medial')
    assert smooth_edge(edge)==edge
    edge['provenance']='authored-estimated'
    assert smooth_edge(edge)==edge
