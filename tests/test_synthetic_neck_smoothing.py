"""Separate degree-two split artifacts from explicit source profile variation."""
import numpy as np
import pytest

from vv_toolbox.model import Segment, VesselGraph
from vv_toolbox.surface import network_mesh, _arterial_junctions


@pytest.mark.parametrize('variable', [False, True])
def test_degree_two_split_does_not_inflate_explicit_radius_profile(variable):
    points = np.column_stack([np.zeros(81), np.zeros(81), np.linspace(0, 40, 81)])
    radii = 3 + .4*np.sin(points[:, 2]/3) if variable else np.full(81, 3.)
    original_points, original_radii = points.copy(), radii.copy()
    whole = VesselGraph({'a': points[0], 'b': points[-1]},
        [Segment('whole', 'a', 'b', points, 3., radii)], {})
    split = VesselGraph({'a': points[0], 'j': points[40], 'b': points[-1]},
        [Segment('source', 'a', 'j', points[:41], 3., radii[:41]),
         Segment('bridge', 'j', 'b', points[40:], 3., radii[40:])], {})
    assert _arterial_junctions(split) == {}
    v0, f0 = network_mesh(whole, spacing=.4)
    v1, f1 = network_mesh(split, spacing=.4)
    np.testing.assert_array_equal(v0, v1)
    np.testing.assert_array_equal(f0, f1)
    np.testing.assert_array_equal(points, original_points)
    np.testing.assert_array_equal(radii, original_radii)
    if not variable:
        interior = v1[(v1[:, 2] > 15) & (v1[:, 2] < 25)]
        assert np.max(np.linalg.norm(interior[:, :2], axis=1)) <= 3.05
