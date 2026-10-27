import numpy as np
import pytest

from vv_toolbox.patch_boundary import patch_boundary_loops
from vv_toolbox.quality_stitch import quality_stitch
from vv_toolbox.ring_stitch import stitch_rings


def inverse_quality(v, f):
    p = v[f]
    return np.sum(np.sum((np.roll(p, -1, axis=1)-p)**2, axis=(1, 2)) /
                  (2*np.sqrt(3)*np.linalg.norm(np.cross(p[:, 1]-p[:, 0],
                                                      p[:, 2]-p[:, 0]), axis=1)))


def test_annulus_boundary_and_objective():
    ta = np.arange(16)*2*np.pi/16
    tb = np.arange(11)*2*np.pi/11
    a = np.column_stack([np.cos(ta), np.sin(ta), np.zeros(16)])
    radius = 1.4+.15*np.sin(tb*3)
    b = np.column_stack([radius*np.cos(tb), radius*np.sin(tb), np.full(11, .2)])
    v = np.vstack([a, b])
    ids_a, ids_b = np.arange(16), np.arange(16, 27)
    faces = quality_stitch(v, ids_a, ids_b)
    baseline = stitch_rings(ids_a, ta, ids_b, tb)
    assert inverse_quality(v, faces) <= inverse_quality(v, baseline)+1e-10
    loops = patch_boundary_loops(faces, np.arange(len(faces)))
    assert {frozenset(x) for x in loops} == {frozenset(ids_a), frozenset(ids_b)}
    assert len(faces) == 27
    assert np.array_equal(faces, quality_stitch(v+100, ids_a, ids_b))


def test_degenerate_geometry_rejected():
    with pytest.raises(ValueError, match='nondegenerate'):
        quality_stitch(np.zeros((6, 3)), [0, 1, 2], [3, 4, 5])


def test_reference_orientation_is_enforced():
    angle = np.arange(12)*2*np.pi/12
    ring = np.column_stack([np.cos(angle), np.sin(angle), np.zeros(12)])
    vertices = np.vstack([ring, ring*2])
    normals = np.tile([0., 0., -1.], (24, 1))
    faces = quality_stitch(vertices, np.arange(12), np.arange(12, 24), normals)
    triangles = vertices[faces]
    cross = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    assert np.all(cross[:, 2] < 0)
    with pytest.raises(ValueError, match='nondegenerate'):
        quality_stitch(vertices, np.arange(12), np.arange(12, 24), -normals)
