import numpy as np
import pytest
import trimesh

from vv_toolbox.model import tube_mesh
from vv_toolbox.estimated_tube_volume import cap_estimated_neck
from vv_toolbox.union_radius import scale_selected_radius


def fixture():
    points=np.array([[0.,0,z] for z in [-2,0,2,4,6]])
    v,f=tube_mesh(points,1.,sides=16)
    closed=cap_estimated_neck(dict(vertices=v,faces=f,metadata=dict(
        kind='estimated-neck-connector',original_atlas_geometry=False)),max_planarity_mm=.001)
    mesh=trimesh.Trimesh(closed['vertices'],closed['faces'],process=False)
    selected=(mesh.triangles_center[:,2]>0)&(mesh.triangles_center[:,2]<4)
    lineage=dict(source_names=['middle','rest'],face_source_indices=(~selected).astype(int).tolist(),
                 source_face_indices=list(range(len(mesh.faces))))
    return mesh,lineage


def test_radius_change_preserves_union_and_other_sources():
    mesh,lineage=fixture();original=mesh.vertices.copy()
    changed,report=scale_selected_radius(mesh,lineage,'middle',[[0,0,0],[0,0,2],[0,0,4]],
        scale=.9,transition_mm=1.,max_displacement_mm=.2)
    middle=np.isclose(original[:,2],2)
    assert np.linalg.norm(changed.vertices[middle,:2],axis=1)==pytest.approx(.9,abs=1e-6)
    assert np.array_equal(changed.vertices[~middle],original[~middle])
    assert np.array_equal(mesh.vertices,original) and np.array_equal(changed.faces,mesh.faces)
    assert report['shared_vertices_fixed'] and report['other_source_vertices_fixed']
    assert changed.is_volume


def test_excessive_change_rejected():
    mesh,lineage=fixture()
    with pytest.raises(ValueError,match='displacement'):
        scale_selected_radius(mesh,lineage,'middle',[[0,0,0],[0,0,4]],
                              scale=2.,transition_mm=1.,max_displacement_mm=.2)


def test_duplicate_centerline_stations_rejected():
    mesh,lineage=fixture()
    with pytest.raises(ValueError,match='Distinct'):
        scale_selected_radius(mesh,lineage,'middle',[[0,0,0],[0,0,0]],
                              scale=.9,transition_mm=1.,max_displacement_mm=.2)


def test_fixed_interface_faces_preserve_seam_triangles_and_allow_interior_edit():
    points=np.array([[0.,0,z] for z in range(-2,9)])
    v,f=tube_mesh(points,1.,sides=16)
    closed=cap_estimated_neck(dict(vertices=v,faces=f,metadata=dict(
        kind='estimated-neck-connector',original_atlas_geometry=False)),max_planarity_mm=.001)
    mesh=trimesh.Trimesh(closed['vertices'],closed['faces'],process=False)
    selected=(mesh.triangles_center[:,2]>0)&(mesh.triangles_center[:,2]<6)
    lineage=dict(source_names=['middle','rest'],face_source_indices=(~selected).astype(int).tolist(),
                 source_face_indices=list(range(len(mesh.faces))))
    changed,report=scale_selected_radius(mesh,lineage,'middle',[[0,0,0],[0,0,6]],
        scale=.9,transition_mm=1.,max_displacement_mm=.2,protect_interface_faces=True)
    shared=np.intersect1d(np.unique(mesh.faces[selected]),np.unique(mesh.faces[~selected]))
    protected=np.any(np.isin(mesh.faces,shared),axis=1)
    assert np.array_equal(changed.triangles[protected],mesh.triangles[protected])
    assert np.array_equal(changed.triangles[~selected],mesh.triangles[~selected])
    assert report['interface_faces_fixed'] and report['moved_vertices']>0
    middle=np.isclose(mesh.vertices[:,2],3)
    assert np.linalg.norm(changed.vertices[middle,:2],axis=1)==pytest.approx(.9,abs=1e-6)


def test_protection_rejects_a_region_with_no_editable_interior():
    mesh,lineage=fixture()
    with pytest.raises(ValueError,match='No editable vertices'):
        scale_selected_radius(mesh,lineage,'middle',[[0,0,0],[0,0,4]],
            scale=.9,transition_mm=1.,max_displacement_mm=.2,protect_interface_faces=True)


def test_explicit_contact_face_is_fixed_while_other_vertices_move():
    mesh,lineage=fixture()
    selected=np.flatnonzero(np.asarray(lineage['face_source_indices'])==0)
    face=int(selected[0])
    changed,report=scale_selected_radius(mesh,lineage,'middle',[[0,0,0],[0,0,4]],
        scale=.9,transition_mm=1.,max_displacement_mm=.2,protected_face_ids=[face])
    assert np.array_equal(changed.triangles[face],mesh.triangles[face])
    assert report['protected_faces_fixed'] and report['protected_face_ids']==[face]
    assert report['moved_vertices']>0
    assert np.array_equal(changed.faces,mesh.faces)


@pytest.mark.parametrize('protected', [[-1],[100000],[0,0],[.5],[True]])
def test_invalid_explicit_face_protection_rejected(protected):
    mesh,lineage=fixture()
    with pytest.raises(ValueError,match='protected face IDs'):
        scale_selected_radius(mesh,lineage,'middle',[[0,0,0],[0,0,4]],
            scale=.9,transition_mm=1.,max_displacement_mm=.2,protected_face_ids=protected)
