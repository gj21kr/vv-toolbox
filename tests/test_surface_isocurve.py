import numpy as np
import trimesh
from vv_toolbox.surface_isocurve import extract_surface_isocurve


def test_plane_on_closed_box_produces_one_closed_loop():
    mesh=trimesh.creation.box(extents=[2,2,2])
    result=extract_surface_isocurve(mesh.vertices,mesh.faces,mesh.vertices[:,2]-.2)
    assert result['status']=='EXTRACTED' and len(result['components'])==1
    loop=result['components'][0]
    assert loop['closed']
    assert np.allclose(np.array(loop['points_mm'])[:,2],.2)
    assert np.allclose(np.ptp(loop['points_mm'],axis=0),[2,2,0])


def test_zero_vertices_are_not_silently_dropped():
    result=extract_surface_isocurve([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],[0,1,-1])
    assert result['status']=='UNKNOWN'


def test_open_contour_is_reported_open():
    result=extract_surface_isocurve([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],[-1,1,1])
    assert not result['components'][0]['closed']
