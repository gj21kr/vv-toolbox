"""Independent rendered-surface crossing checks, not clinical collision validation."""
import numpy as np
import pytest
from hashlib import sha256
from scipy.spatial import cKDTree

from vv_toolbox.atlas import ROOT, load_atlas
from vv_toolbox.atlas_neck import build_neck_repairs, _terminal


def _edge_hits_triangles(start, end, triangles, epsilon=1e-8):
    """Vectorized Moller-Trumbore finite segment test; coplanar pairs excluded."""
    direction = end - start
    edge1 = triangles[:, 1] - triangles[:, 0]
    edge2 = triangles[:, 2] - triangles[:, 0]
    h = np.cross(direction, edge2)
    determinant = np.einsum('ij,ij->i', edge1, h)
    valid = np.abs(determinant) > epsilon
    inverse = np.divide(1., determinant, out=np.zeros_like(determinant), where=valid)
    offset = start - triangles[:, 0]
    u = inverse * np.einsum('ij,ij->i', offset, h)
    q = np.cross(offset, edge1)
    v = inverse * np.sum(direction * q, axis=-1)
    t = inverse * np.einsum('ij,ij->i', edge2, q)
    return valid & (u >= -epsilon) & (v >= -epsilon) & (u+v <= 1+epsilon) & (t >= -epsilon) & (t <= 1+epsilon)


def surface_crossings(vertices_a, faces_a, vertices_b, faces_b):
    """Count intersecting triangle pairs using safe sphere + AABB broad phases.

    All six finite edges are checked, including a small triangle crossing the
    interior of a large one. Does not certify coplanar overlap or containment.
    """
    a = np.asarray(vertices_a, float)[faces_a]
    b = np.asarray(vertices_b, float)[faces_b]
    centers_b = b.mean(axis=1)
    radii_b = np.linalg.norm(b-centers_b[:, None], axis=2).max(axis=1)
    tree = cKDTree(centers_b)
    low_b, high_b = b.min(axis=1), b.max(axis=1)
    candidates = hits = 0
    maximum_radius_b = radii_b.max()
    for triangle in a:
        center = triangle.mean(axis=0)
        radius = np.linalg.norm(triangle-center, axis=1).max()
        indices = np.asarray(tree.query_ball_point(center, radius+maximum_radius_b+1e-8), int)
        if not len(indices):
            continue
        indices = indices[np.all(high_b[indices] >= triangle.min(axis=0)-1e-8, axis=1)
                          & np.all(low_b[indices] <= triangle.max(axis=0)+1e-8, axis=1)]
        if not len(indices):
            continue
        candidates += len(indices)
        other = b[indices]
        crossed = np.zeros(len(other), bool)
        for edge in range(3):
            crossed |= _edge_hits_triangles(triangle[edge], triangle[(edge+1) % 3], other)
            crossed |= _edge_hits_triangles(other[:, edge], other[:, (edge+1) % 3],
                                            np.broadcast_to(triangle, other.shape))
        hits += int(crossed.sum())
    return {'aabb_candidate_pairs': candidates, 'noncoplanar_intersecting_pairs': hits}


def test_surface_crossing_detector_catches_both_edge_directions_and_clear_pair():
    large = np.array([[-5., -5, 0], [5, -5, 0], [0, 5, 0]])
    small = np.array([[0., 0, -1], [.2, 0, 1], [0, .2, 1]])
    face = np.array([[0, 1, 2]])
    for a, b in [(large, small), (small, large)]:
        assert surface_crossings(a, face, b, face)['noncoplanar_intersecting_pairs'] == 1
    assert surface_crossings(large, face, small+[0, 0, 5], face)['noncoplanar_intersecting_pairs'] == 0


@pytest.mark.skipif(not (ROOT/'isa_BP3D_4.0_obj_99.zip').exists(), reason='Optional official local atlas absent')
def test_actual_atlas_estimated_arteries_do_not_cross_fused_venous_surface():
    atlas = load_atlas()
    def fingerprints():
        return {p['id']: (sha256(p['vertices'].tobytes()).hexdigest(),
                          sha256(p['faces'].tobytes()).hexdigest()) for p in atlas.meshes}
    original = fingerprints()
    source = {p['id']: p for p in atlas.meshes}
    anchors = {side: _terminal(source[element], True)
               for side, element in [('right', 'FJ3585'), ('left', 'FJ3485')]}
    parts, _ = build_neck_repairs(atlas)
    assert fingerprints() == original
    arteries = [p for p in parts if p['layer'] == 'arterial']
    veins = [p for p in parts if p['layer'] == 'systemic_venous']
    assert len(arteries) == 4 and len(veins) == 1
    segments = {s['id']: s for s in veins[0]['metadata']['graph']['segments']}
    for side in ('right', 'left'):
        extension = segments[side+'_internal_jugular_extension']
        points = np.asarray(extension['points_mm'])
        np.testing.assert_allclose(points[0], anchors[side]['center'], atol=1e-10)
        direction = points[1]-points[0]
        assert np.dot(direction/np.linalg.norm(direction), anchors[side]['axis']) > .995
        following = segments[side+'_sigmoid_lower']
        next_points = np.asarray(following['points_mm'])
        np.testing.assert_array_equal(points[-1], next_points[0])
        assert extension['radius_profile_mm'][-1] == following['radius_profile_mm'][0]
        outgoing, incoming = points[-1]-points[-2], next_points[1]-next_points[0]
        assert np.dot(outgoing, incoming)/(np.linalg.norm(outgoing)*np.linalg.norm(incoming)) > .995
    for artery in arteries:
        for vein in veins:
            result = surface_crossings(artery['vertices'], artery['faces'], vein['vertices'], vein['faces'])
            print(artery['id'], result)
            assert result['noncoplanar_intersecting_pairs'] == 0, (artery['id'], vein['id'], result)
