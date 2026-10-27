import numpy as np
import trimesh
from vv_toolbox.section_centering import center_section_path


def test_centroid_proposal_preserves_fixed_chords_and_is_bounded():
    mesh=trimesh.creation.box(extents=[12,4,4])
    points=np.column_stack([np.linspace(-4,4,9),np.full(9,.3),np.zeros(9)])
    fixed=[0,1,7,8]
    result,meta=center_section_path(mesh,points,fixed_indices=fixed,max_displacement_mm=.5,max_turn_degrees=30.)
    assert meta['status']=='CANDIDATE' and meta['after_residual_mm2']<meta['before_residual_mm2']
    assert meta['containment']['status']=='PASS'
    np.testing.assert_array_equal(result[fixed],points[fixed])
    assert np.linalg.norm(result-points,axis=1).max()<=.5


def test_no_silent_limit_relaxation():
    mesh=trimesh.creation.box(extents=[12,4,4])
    points=np.column_stack([np.linspace(-4,4,9),np.full(9,.3),np.zeros(9)])
    result,meta=center_section_path(mesh,points,fixed_indices=[0,8],max_displacement_mm=.001,max_turn_degrees=30.)
    assert meta['status']=='NO_ACCEPTED_CHANGE'
    np.testing.assert_array_equal(result,points)
