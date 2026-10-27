import numpy as np
import trimesh
from vv_toolbox.mesh_neck_opening import build_neck_opening


def test_separate_opening_keeps_exterior_and_has_one_declared_boundary():
    mesh=trimesh.creation.box(extents=[4,4,4]);v=mesh.vertices.copy();f=mesh.faces.copy()
    points=[[-.7,-.6,3],[.8,-.6,3],[.8,.9,3],[-.7,.9,3]]
    vertices,faces,report=build_neck_opening(v,f,points,[0,0,1])
    assert report['retained_triangle_identity']
    np.testing.assert_array_equal(v,mesh.vertices);np.testing.assert_array_equal(f,mesh.faces)
    assert report['new_collar_face_count']>0 and not report['closed_lumen']
    opened=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    assert not opened.is_watertight and opened.is_winding_consistent
