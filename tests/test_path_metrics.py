import numpy as np
import pytest
from vv_toolbox.path_metrics import polyline_metrics


def test_known_bend_and_rigid_motion():
    points = np.array([[0., 0, 0], [3, 0, 0], [3, 4, 0]])
    measured = polyline_metrics(points)
    assert measured['length_mm'] == 7
    assert measured['chord_mm'] == 5
    assert measured['length_over_chord'] == 1.4
    assert measured['maximum_turn_deg'] == 90
    shifted = polyline_metrics(points[:, [2, 0, 1]] + [10, 20, 30])
    assert measured == shifted


def test_straight_and_closed_path():
    assert polyline_metrics([[0, 0, 0], [0, 0, 2]])['length_over_chord'] == 1
    closed = polyline_metrics([[0, 0, 0], [0, 0, 2], [0, 0, 0]])
    assert closed['length_over_chord'] is None
    assert closed['ratio_status'] == 'UNDEFINED_COINCIDENT_ENDPOINTS'


@pytest.mark.parametrize('points', [[[0, 0, 0]], [[0, 0, 0], [0, 0, 0]], [[0, 0, 0], [float('nan'), 0, 0]]])
def test_invalid_paths_rejected(points):
    with pytest.raises(ValueError):
        polyline_metrics(points)
