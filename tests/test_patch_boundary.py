import numpy as np
import pytest
from vv_toolbox.patch_boundary import patch_boundary_loops,vertices_to_closed_curve_distance


def test_boundary_uses_original_vertex_ids_and_excludes_diagonal():
    faces=[[4,7,9],[4,9,12]]
    assert patch_boundary_loops(faces,[0,1])==[[4,7,9,12]]


def test_vertex_touching_components_cannot_be_one_loop():
    with pytest.raises(ValueError,match='simple'):
        patch_boundary_loops([[0,1,2],[0,3,4]],[0,1])


def test_distance_is_to_segments_not_just_vertices():
    d=vertices_to_closed_curve_distance([[1,0,0],[1,0,1]],
        [[0,0,0],[2,0,0],[2,2,0],[0,2,0]])
    assert np.allclose(d,[0,1])
