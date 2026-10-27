import numpy as np
import pytest
import trimesh
from vv_toolbox.contained_path_smoothing import smooth_contained_path


def test_zigzag_smoothed_inside_without_changing_end_chords():
    mesh=trimesh.creation.box(extents=[8,4,4])
    points=np.column_stack([np.linspace(-3,3,9),[0,0,.6,-.6,.6,-.6,.6,0,0],np.zeros(9)])
    original=points.copy();fixed=[0,1,7,8]
    candidate,meta=smooth_contained_path(mesh,points,fixed_indices=fixed,max_displacement_mm=.8)
    assert meta['after']['maximum_turn_deg']<meta['before']['maximum_turn_deg']
    assert meta['containment']['status']=='PASS' and meta['maximum_displacement_mm']<=.8
    np.testing.assert_array_equal(candidate[fixed],original[fixed]);np.testing.assert_array_equal(points,original)


def test_outside_initial_path_is_rejected():
    with pytest.raises(ValueError,match='Initially contained'):
        smooth_contained_path(trimesh.creation.box(),[[0,0,0],[2,0,0],[0,.1,0]],
            fixed_indices=[0,2],max_displacement_mm=.5)
