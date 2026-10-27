import numpy as np
import pytest
from vv_toolbox.geometry_quality import segment_closest_points, segment_distance


@pytest.mark.parametrize('points,expected', [
    ([[0,0,0],[2,0,0],[1,-1,0],[1,1,0]], (0,.5,.5)),
    ([[0,0,0],[1,0,0],[2,1,0],[2,2,0]], (2**.5,1,0)),
    ([[0,0,0],[2,0,0],[0,3,0],[2,3,0]], (3,0,0)),
])
def test_exact_witness(points, expected):
    distance, s, t, p, q = segment_closest_points(*points)
    assert (distance,s,t) == pytest.approx(expected)
    assert np.linalg.norm(p-q) == pytest.approx(distance)
    assert np.allclose(p, np.asarray(points[0])+s*(np.asarray(points[1])-points[0]))
    assert np.allclose(q, np.asarray(points[2])+t*(np.asarray(points[3])-points[2]))
    assert segment_distance(*points) == pytest.approx(distance)


def test_reversed_witness_geometry():
    points = [[0,0,0],[4,0,0],[1,-2,3],[1,2,3]]
    a = segment_closest_points(*points)
    b = segment_closest_points(points[1],points[0],points[3],points[2])
    assert a[0] == pytest.approx(b[0])
    assert a[1] == pytest.approx(1-b[1])
    assert a[2] == pytest.approx(1-b[2])


def test_zero_length_rejected():
    with pytest.raises(ValueError, match='nonzero'):
        segment_closest_points([0,0,0],[0,0,0],[1,0,0],[2,0,0])
