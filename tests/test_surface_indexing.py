import numpy as np
import trimesh

from vv_toolbox.surface_indexing import exact_vertex_index_copy


def separated_indices():
    box=trimesh.creation.box()
    points=np.asarray(box.vertices[box.faces]).reshape(-1,3)
    return trimesh.Trimesh(points,np.arange(len(points)).reshape(-1,3),process=False)


def test_duplicate_indices_close_without_changing_any_triangle():
    mesh=separated_indices()
    before_vertices=mesh.vertices.copy();before_faces=mesh.faces.copy()
    result,report=exact_vertex_index_copy(mesh)
    assert not mesh.is_watertight and result.is_watertight
    assert report['usable_for_sampled_containment']
    assert report['original_vertices']==36 and report['normalized_vertices']==8
    assert np.array_equal(result.vertices[result.faces],mesh.vertices[mesh.faces])
    assert np.array_equal(mesh.vertices,before_vertices) and np.array_equal(mesh.faces,before_faces)
    assert result.contains([[0,0,0],[2,0,0]]).tolist()==[True,False]
    assert report['self_intersection']=='NOT RUN'


def test_real_missing_face_is_not_capped():
    mesh=separated_indices()
    mesh=trimesh.Trimesh(mesh.vertices,mesh.faces[:-1],process=False)
    result,report=exact_vertex_index_copy(mesh)
    assert not result.is_watertight
    assert not report['usable_for_sampled_containment']
    assert len(result.faces)==len(mesh.faces)


def test_nearby_vertices_are_not_welded():
    mesh=separated_indices()
    mesh.vertices[0,0]+=1e-8
    result,report=exact_vertex_index_copy(mesh)
    assert report['normalized_vertices']==9
    assert not report['usable_for_sampled_containment']
    assert np.array_equal(result.vertices[result.faces],mesh.vertices[mesh.faces])


def test_inconsistent_winding_is_not_accepted():
    mesh=separated_indices()
    mesh.faces[0]=mesh.faces[0][::-1]
    _,report=exact_vertex_index_copy(mesh)
    assert not report['normalized_winding_consistent']
    assert not report['usable_for_sampled_containment']
