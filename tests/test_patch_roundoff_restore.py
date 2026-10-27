import numpy as np
import pytest

from vv_toolbox.patch_roundoff_restore import restore_patch_coordinates


def test_roundoff_restore_is_exact_and_preserves_unselected_vertices():
    v=np.array([[0.,0,0],[1,0,0],[0,1,0],[4,4,4]])
    f=np.array([[0,1,2]]);patch=dict(vertices=v[:3].copy(),faces=f.copy())
    moved=v.copy();moved[:3]+=1e-12
    restored,report=restore_patch_coordinates(moved,f,[0],patch,max_roundoff_mm=1e-8)
    assert np.array_equal(restored,v) and report['protected_positions_exact']
    assert not np.array_equal(moved[:3],v[:3])


@pytest.mark.parametrize('change',['position','winding'])
def test_changed_geometry_or_orientation_is_rejected(change):
    v=np.array([[0.,0,0],[1,0,0],[0,1,0]]);f=np.array([[0,1,2]])
    patch=dict(vertices=v.copy(),faces=f.copy())
    if change=='position':v[0,0]+=.01
    else:f=f[:,::-1]
    with pytest.raises(ValueError):restore_patch_coordinates(v,f,[0],patch,max_roundoff_mm=1e-8)
