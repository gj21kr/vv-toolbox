import numpy as np
import pytest
from vv_toolbox.triangle_neck_cut import partition_triangle


def area(points):
    return sum(np.linalg.norm(np.cross(points[i]-points[0],points[i+1]-points[0]))/2
               for i in range(1,len(points)-1))


@pytest.mark.parametrize('reverse',[False,True])
@pytest.mark.parametrize('shift',[0.,10.,-10.])
def test_partition_preserves_source_plane_area_and_orientation(reverse,shift):
    source=np.array([[-3.,-2.,-7.],[3.,-2.,5.],[0.,4.,5.]])
    neck=np.array([[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]])+shift
    if reverse:neck=neck[::-1]
    inside,outside=partition_triangle(source[:,:2],neck)
    pieces=([inside] if len(inside) else [])+outside
    assert sum(area(b@source) for b in pieces)==pytest.approx(area(source),abs=1e-10)
    normal=np.cross(source[1]-source[0],source[2]-source[0])
    for bary in pieces:
        assert np.all(bary>=-1e-12)
        np.testing.assert_allclose(bary.sum(1),1.)
        points=bary@source
        np.testing.assert_allclose((points-source[0])@normal,0.,atol=1e-10)
        assert np.cross(points[1]-points[0],points[2]-points[0])@normal>=-1e-10
    assert bool(len(inside))==(shift==0)


def test_enclosing_neck_removes_whole_triangle_and_edge_touch_removes_nothing():
    tri=np.array([[0.,0.],[1.,0.],[0.,1.]])
    inside,outside=partition_triangle(tri,[[-2,-2],[2,-2],[2,2],[-2,2]])
    np.testing.assert_array_equal(inside,np.eye(3));assert not outside
    inside,outside=partition_triangle(tri,[[0,-1],[1,-1],[1,0],[0,0]])
    assert not len(inside)
    assert sum(area(np.column_stack([b@tri,np.zeros(len(b))])) for b in outside)==pytest.approx(.5)


def test_concave_neck_is_rejected():
    with pytest.raises(ValueError,match='Convex'):
        partition_triangle([[0,0],[2,0],[0,2]],[[0,0],[2,0],[1,.5],[2,2],[0,2]])
