import numpy as np
import trimesh
from vv_toolbox.source_neck_opening import build_source_neck_opening
from vv_toolbox.patch_boundary import patch_boundary_loops


def test_conforming_source_cut_preserves_surface_and_opening_area():
    source=trimesh.creation.box(extents=[4,4,4])
    v,f,meta=build_source_neck_opening(source.vertices,source.faces,
        [[-.7,-.6,3],[.8,-.6,3],[.8,.9,3],[-.7,.9,3]],[0,0,1])
    mesh=trimesh.Trimesh(vertices=v,faces=f,process=False)
    assert mesh.is_winding_consistent
    assert len(patch_boundary_loops(f,np.arange(len(f))))==1
    np.testing.assert_allclose(mesh.area,source.area-1.5*1.5,atol=1e-10)
    for tri,index in zip(v[f],meta['source_face_ids']):
        original=source.triangles[index];normal=source.face_normals[index]
        np.testing.assert_allclose((tri-original[0])@normal,0,atol=1e-10)
