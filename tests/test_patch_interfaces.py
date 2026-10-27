import numpy as np
import trimesh

from vv_toolbox.patch_interfaces import inspect_patch_interfaces


def test_closed_source_has_paired_boundary_edges():
    mesh = trimesh.creation.box()
    result = inspect_patch_interfaces(mesh.faces, [0])
    assert result['status'] == 'PASS'
    assert result['boundary_edge_count'] == 3
    assert all(r['selected_face_ids'] == [0] and len(r['complement_face_ids']) == 1
               for r in result['loops'][0]['edges'])


def test_open_source_does_not_claim_interface():
    result = inspect_patch_interfaces([[0,1,2]], [0])
    assert result['status'] == 'FAIL'
    assert all(not r['complement_face_ids'] for r in result['loops'][0]['edges'])


def test_same_winding_is_rejected():
    mesh = trimesh.creation.box()
    faces = mesh.faces.copy()
    faces[0] = faces[0][::-1]
    assert inspect_patch_interfaces(faces, [0])['status'] == 'FAIL'


def test_whole_closed_surface_has_no_reconnection_interface():
    mesh = trimesh.creation.box()
    assert inspect_patch_interfaces(mesh.faces, np.arange(len(mesh.faces)))['status'] == 'UNKNOWN'
