import numpy as np
import pytest

from vv_toolbox.angular_ring import angular_ring, stitch_polar_rings
from vv_toolbox.patch_boundary import patch_boundary_loops


def test_unequal_seam_phases_preserve_original_boundary_edges():
    a, b = np.arange(7), np.arange(7, 18)
    ta = np.arange(7)*2*np.pi/7+.02
    tb = np.arange(11)*2*np.pi/11+.07
    faces = stitch_polar_rings(a, ta, b, tb)
    loops = patch_boundary_loops(faces, np.arange(len(faces)))
    assert len(faces) == 18
    assert {frozenset(loop) for loop in loops} == {frozenset(a), frozenset(b)}
    edges = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]],
                                              faces[:, [2, 0]]]), axis=1), axis=0)
    assert 18-len(edges)+len(faces) == 0


def test_geometry_phase_preserved_and_clockwise_reversed():
    angles = np.array([.1, 1.4, 3., 4.8])
    vertices = np.column_stack([np.cos(angles), np.sin(angles), np.zeros(4)])
    ids, phase = angular_ring([2, 1, 0, 3], vertices, np.zeros(3), np.eye(3))
    np.testing.assert_array_equal(ids, np.arange(4))
    np.testing.assert_allclose(phase, angles)


def test_non_star_shaped_ring_rejected_without_sorting():
    angles = np.array([.1, 1.4, 1.2, 3., 4.8])
    vertices = np.column_stack([np.cos(angles), np.sin(angles), np.zeros(5)])
    with pytest.raises(ValueError, match='star-shaped'):
        angular_ring(np.arange(5), vertices, np.zeros(3), np.eye(3))
