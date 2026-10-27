import numpy as np
import pytest

from vv_toolbox.collar_link import build_collar_link
from vv_toolbox.collar_link import build_radius_collar


def test_oriented_straight_link_retains_sources_and_exact_anchors():
    a, b = np.array([[0., 0, 0], [10, 0, 0]]), np.array([[20., 0, 0], [30, 0, 0]])
    before = a.copy(), b.copy()
    result = build_collar_link(a, b, collar_mm=2)
    assert np.array_equal(a, before[0]) and np.array_equal(b, before[1])
    assert result["points_mm"][0].tolist() == [8, 0, 0]
    assert result["points_mm"][-1].tolist() == [22, 0, 0]
    assert np.allclose(result["points_mm"][:, 0], np.linspace(8, 22, 129))
    assert result["report"]["sampled_start_angle_deg"] == 0
    assert result["report"]["surface_containment"] == "NOT RUN"


def test_reversed_traversal_changes_tangents_consistently():
    result = build_collar_link([[30, 0, 0], [20, 0, 0]], [[10, 0, 0], [0, 0, 0]], collar_mm=2)
    assert result["points_mm"][0].tolist() == [22, 0, 0]
    assert result["points_mm"][-1].tolist() == [8, 0, 0]
    assert result["report"]["sampled_end_angle_deg"] == 0


@pytest.mark.parametrize("collar", [0, float("nan"), True, 10])
def test_invalid_or_overlong_collars_rejected(collar):
    with pytest.raises(ValueError):
        build_collar_link([[0, 0, 0], [10, 0, 0]], [[20, 0, 0], [30, 0, 0]], collar_mm=collar)


def test_radius_interpolates_source_anchors_and_preserves_retained_samples():
    result = build_radius_collar([[0, 0, 0], [10, 0, 0]], [[20, 0, 0], [30, 0, 0]],
                                [1, 3], [4, 9], collar_mm=2)
    assert result["report"]["endpoint_radii_mm"] == pytest.approx([2.6, 5])
    assert result["retained_incoming"]["radii_mm"].tolist() == pytest.approx([1, 2.6])
    assert result["retained_outgoing"]["radii_mm"].tolist() == pytest.approx([5, 9])
    assert np.array_equal(result["retained_incoming"]["points_mm"][-1], result["points_mm"][0])
    assert np.array_equal(result["retained_outgoing"]["points_mm"][0], result["points_mm"][-1])
    assert np.all(np.diff(result["radii_mm"]) >= 0)


def test_anchor_at_source_knot_does_not_duplicate_retained_points():
    result = build_radius_collar([[0, 0, 0], [5, 0, 0], [10, 0, 0]],
                                [[20, 0, 0], [25, 0, 0], [30, 0, 0]],
                                [1, 2, 3], [4, 5, 6], collar_mm=5)
    for name in ("retained_incoming", "retained_outgoing"):
        assert np.all(np.linalg.norm(np.diff(result[name]["points_mm"], axis=0), axis=1) > 0)


@pytest.mark.parametrize("radii", [[1], [1, 0], [1, float("nan")]])
def test_invalid_source_radii_rejected(radii):
    with pytest.raises(ValueError):
        build_radius_collar([[0, 0, 0], [10, 0, 0]], [[20, 0, 0], [30, 0, 0]],
                            radii, [1, 2], collar_mm=2)
