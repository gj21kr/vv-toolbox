import numpy as np
import pytest
from vv_toolbox.adjacent_contact import overlap_beyond_shared


@pytest.mark.parametrize('other,shared,expected', [
    ([[0,0,0],[1,0,0],[0,-1,0]], [[0,0,0],[1,0,0]], False),
    ([[0,0,0],[1,0,0],[.2,.2,0]], [[0,0,0],[1,0,0]], True),
    ([[0,0,0],[1,0,0],[0,0,1]], [[0,0,0],[1,0,0]], False),
    ([[0,0,0],[-1,0,0],[0,-1,0]], [[0,0,0]], False),
    ([[0,0,0],[.4,.1,0],[.1,.4,0]], [[0,0,0]], True),
    ([[0,0,0],[.4,.2,-1],[.4,.2,1]], [[0,0,0]], True),
    ([[0,0,0],[-.4,-.2,-1],[-.4,-.2,1]], [[0,0,0]], False),
])
def test_expected_shared_topology(other, shared, expected):
    a = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
    b, s = np.array(other, dtype=float), np.array(shared, dtype=float)
    assert overlap_beyond_shared(a,b,s) == expected
    rotation = np.array([[0.,0.,1.],[1.,0.,0.],[0.,1.,0.]])
    assert overlap_beyond_shared(a@rotation+1500,b@rotation+1500,s@rotation+1500) == expected


def test_tilted_coplanar_distance_is_measured_in_3d():
    a = np.array([[0.,0.,0.],[1.,0.,0.],[0.,.8e-8,.8e-8]])
    b = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.6e-8,1.6e-8]])
    assert overlap_beyond_shared(a, b, a[:2], tolerance_mm=1e-8)


def test_adjacent_near_parallel_faces_are_not_a_clearance_test():
    a = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
    b = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,1e-9]])
    assert not overlap_beyond_shared(a, b, a[:2], tolerance_mm=1e-8)


def test_subdivided_atlas_triangle_shared_point_is_not_overlap():
    # Source subdivision children share one midpoint. Their planes differ
    # slightly in floating point; each remains on one side of the other plane.
    a = np.array([[-36.907501220703125,-107.49099731445312,1544.260009765625],
                  [-36.36130142211914,-108.01499938964844,1543.72998046875],
                  [-36.628501892089844,-107.51899719238281,1543.7650146484375]])
    b = np.array([[-37.17469787597656,-106.99500274658203,1544.2950439453125],
                  [-36.628501892089844,-107.51899719238281,1543.7650146484375],
                  [-36.89569854736328,-107.02300262451172,1543.800048828125]])
    for offset in (np.zeros(3), -a[2]):
        assert not overlap_beyond_shared(a+offset, b+offset, a[2:]+offset)
