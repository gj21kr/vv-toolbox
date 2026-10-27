import numpy as np
import pytest
import trimesh

from vv_toolbox.collar_surface import build_sampled_wall, inspect_wall_vertices


def test_wall_rings_follow_radius_and_do_not_modify_source():
    points = np.array([[0., 0, -1], [0, 0, 0], [0, 0, 1]])
    before = points.copy()
    wall = build_sampled_wall(points, [1, 2, 3], sides=16)
    rings = wall.vertices.reshape(3, 16, 3)
    assert np.allclose(np.linalg.norm(rings-points[:, None], axis=2), np.array([1, 2, 3])[:, None])
    assert np.array_equal(points, before)
    assert len(wall.faces) == 64
    assert not wall.is_watertight


def test_inside_vertices_do_not_approve_whole_wall():
    wall = build_sampled_wall([[0, 0, -1], [0, 0, 1]], [1, 1])
    report = inspect_wall_vertices(trimesh.creation.box(extents=[10, 10, 10]), wall)
    assert report["status"] == "UNKNOWN"
    assert report["outside_count"] == 0
    assert report["whole_wall_containment"] == "NOT RUN"


def test_actual_outside_vertex_rejects_wall_containment():
    wall = build_sampled_wall([[0, 0, -1], [0, 0, 1]], [3, 3])
    report = inspect_wall_vertices(trimesh.creation.box(extents=[4, 4, 4]), wall)
    assert report["status"] == "FAIL"
    assert report["outside_count"] > 0
    assert report["witnesses"][0]["distance_mm"] > 1e-6


def test_invalid_radius_rejected():
    with pytest.raises(ValueError):
        build_sampled_wall([[0, 0, 0], [0, 0, 1]], [1, -1])
