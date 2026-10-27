import numpy as np
import pytest
from vv_toolbox.neck_conformity import inspect_neck_conformity


def test_plane_projection_distance_and_span():
    vertices=[[-4,-4,0],[4,-4,0],[4,4,0],[-4,4,0]]
    curve=[[-1,-.5,.2],[1,-.5,.2],[1,.5,.2],[-1,.5,.2]]
    result=inspect_neck_conformity(vertices,[[0,1,2],[0,2,3]],curve,[0,0,0],np.eye(3),
                                   distance_limit_mm=.3)
    assert result['sampled_distance_status']=='PASS'
    assert result['max_distance_mm']==pytest.approx(.2)
    assert result['mapped_projected_width_depth_mm']==pytest.approx([2,1])
    assert result['anatomical_neck_dimensions']=='UNKNOWN'
    failed=inspect_neck_conformity(vertices,[[0,1,2],[0,2,3]],curve,[0,0,0],np.eye(3),
                                   distance_limit_mm=.1)
    assert failed['sampled_distance_status']=='FAIL'


def test_nonorthonormal_measurement_frame_rejected():
    with pytest.raises(ValueError):
        inspect_neck_conformity([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],
            [[0,0,0],[.1,0,0],[0,.1,0]],[0,0,0],2*np.eye(3),distance_limit_mm=.3)
