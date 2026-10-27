from copy import deepcopy
import numpy as np
import pytest
import trimesh

from vv_toolbox.profile_loft import loft_source_profiles
from vv_toolbox.source_sections import extract_source_sections


def profiles():
    mesh=trimesh.creation.box(extents=[2,4,8])
    return extract_source_sections(mesh,[[0,0,z] for z in [-3,-2,-1,0,1,2,3]])['profiles']


def test_open_loft_preserves_nonround_sections_and_source():
    source=profiles();before=deepcopy(source)
    mesh,report=loft_source_profiles(source,samples=48)
    assert source==before and not mesh.is_watertight
    assert report['boundary_edges']==96 and mesh.is_winding_consistent
    assert len(mesh.faces)==2*48*4
    assert mesh.extents==pytest.approx([2,4,4])
    assert report['self_intersection']=='NOT RUN'
    # Sampling this rectangle with 48 equal perimeter intervals retains corners.
    assert mesh.area==pytest.approx(12*4)


def test_reversed_and_shifted_contour_has_no_twisted_seam():
    source=profiles()
    for i,row in enumerate(source):
        ring=np.array(row['contour_xyz_mm'])[:-1]
        if i%2:ring=ring[::-1]
        ring=np.roll(ring,i,axis=0)
        row['contour_xyz_mm']=np.vstack([ring,ring[0]]).tolist()
    mesh,_=loft_source_profiles(source,samples=48)
    assert mesh.area==pytest.approx(48)
    assert mesh.is_winding_consistent


@pytest.mark.parametrize('damage',['missing','unknown','open','zero'])
def test_invalid_profile_chain_rejected(damage):
    source=profiles()
    if damage=='missing':source.pop(2)
    elif damage=='unknown':source[2]['status']='UNKNOWN'
    elif damage=='open':source[2]['contour_xyz_mm'][-1][0]+=1
    else:source[2]['normal']=[0,0,0]
    with pytest.raises(ValueError):loft_source_profiles(source)
