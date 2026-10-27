import numpy as np

from vv_toolbox.planar_patch_flips import improve_planar_patch


def fixture():
    return np.array([[0.,0,0],[3,0,0],[4,1,0],[0,1,0]]),np.array([[0,1,2],[0,2,3]])


def test_planar_convex_diagonal_improves_quality():
    v,f=fixture();before=v.copy()
    changed,report=improve_planar_patch(v,f,[0,1])
    assert report['flips']==1
    assert report['minimum_quality_after']>report['minimum_quality_before']
    assert np.array_equal(v,before)
    assert np.array_equal(f,[[0,1,2],[0,2,3]])
    assert {tuple(sorted(e)) for t in changed for e in zip(t,np.roll(t,-1))}=={(0,1),(1,2),(2,3),(0,3),(1,3)}


def test_selection_boundary_and_nonplanar_geometry_are_preserved():
    v,f=fixture()
    assert np.array_equal(improve_planar_patch(v,f,[0])[0],f)
    v[3,2]=.1
    assert np.array_equal(improve_planar_patch(v,f,[0,1])[0],f)
