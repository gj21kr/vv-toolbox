import numpy as np
import pytest
import trimesh

from vv_toolbox.source_patch import extract_source_patch


def test_selected_triangle_identity_and_source_indices():
    mesh = trimesh.creation.box()
    selected = np.array([3, 1, 7])
    result = extract_source_patch(mesh.vertices, mesh.faces, selected)
    assert np.array_equal(result['vertices'][result['faces']], mesh.vertices[mesh.faces[selected]])
    assert np.array_equal(result['source_face_ids'], selected)
    assert result['report']['source_triangle_identity'] == 'PASS'
    assert np.array_equal(result['vertices'], mesh.vertices[result['source_vertex_ids']])


def test_open_square_has_original_boundary_ids():
    result = extract_source_patch([[0,0,0],[1,0,0],[1,1,0],[0,1,0]], [[0,1,2],[0,2,3]], [0,1])
    assert result['report']['boundary_topology'] == 'SIMPLE_LOOPS'
    assert result['report']['boundary_loops_source_vertex_ids'] == [[0,1,2,3]]


@pytest.mark.parametrize('selection', [[0,0], [20], []])
def test_invalid_face_selection_rejected(selection):
    mesh = trimesh.creation.box()
    with pytest.raises(ValueError):
        extract_source_patch(mesh.vertices, mesh.faces, selection)
