import tracemalloc

import numpy as np
import pytest
import trimesh

from vv_toolbox.voxel_output import _inside


def test_batched_winding_matches_reference_on_boundary_inside_and_outside():
    mesh = trimesh.creation.icosphere(subdivisions=2)
    rng = np.random.default_rng(1729)
    points = np.vstack((mesh.vertices, mesh.triangles_center,
                        mesh.triangles[:, :2].mean(axis=1), rng.uniform(-2, 2, (211, 3))))
    for start in range(0, len(points), 128):
        block = points[start:start+128]
        expected = _inside(block, mesh.triangles, 1e-8, triangle_chunk=32)
        assert np.array_equal(_inside(block, mesh.triangles, 1e-8), expected)


def test_batch_workspace_fits_existing_eight_mib_allowance():
    mesh = trimesh.creation.icosphere(subdivisions=2)
    points = np.random.default_rng(83).normal(size=(128, 3))
    triangles = mesh.triangles.copy()
    tracemalloc.start()
    try:
        _inside(points, triangles, 1e-8)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak <= 8*1024**2


def test_unsupported_batch_rejected():
    with pytest.raises(ValueError, match='triangle batches'):
        _inside(np.zeros((1, 3)), np.zeros((1, 3, 3)), 1e-8, triangle_chunk=1024)
