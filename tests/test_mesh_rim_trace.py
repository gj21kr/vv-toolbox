import numpy as np
import trimesh
from vv_toolbox.mesh_rim_trace import trace_mesh_rim


def test_closed_trace_follows_source_faces_between_rim_samples():
    mesh=trimesh.creation.box(extents=[4,4,4])
    polygon=[[-.7,-.6,3],[.8,-.6,3],[.8,.9,3],[-.7,.9,3]]
    report=trace_mesh_rim(mesh.vertices,mesh.faces,polygon,[0,0,1])
    assert report['closed_within_tolerance'] and report['segment_count']>4
    for side in report['sides']:
        for segment in side['segments']:
            np.testing.assert_allclose(np.asarray(segment['points_mm'])[:,2],2)


def test_multiple_surface_layers_are_not_joined_arbitrarily():
    mesh=trimesh.creation.box(extents=[4,4,1]);other=mesh.copy();other.apply_translation([0,0,3])
    mesh=trimesh.util.concatenate([mesh,other])
    report=trace_mesh_rim(mesh.vertices,mesh.faces,[[-.7,-.6,5],[.8,-.6,5],[.8,.9,5],[-.7,.9,5]],[0,0,1])
    assert report['status']=='UNKNOWN' and not report['closed_within_tolerance']
