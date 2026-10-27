from copy import deepcopy

import pytest

from test_synthetic_routes import fixture
from vv_toolbox.route_junction_measurements import measure_route_junctions


def connected():
    case, _ = fixture()
    case["nodes"].pop("2")
    case["nodes"]["3"]["position_mm"] = [10, 10, 0]
    case["edges"][1].update(start="1", centerline_mm=[[10, 0, 0], [10, 10, 0]])
    return case


def test_oriented_measurements_and_reverse_preserve_source():
    case = connected()
    before = deepcopy(case)
    result = measure_route_junctions(case, dict(edges=["a", "b"], nodes=["0", "1", "3"]))
    backward = measure_route_junctions(case, dict(edges=["b", "a"], nodes=["3", "1", "0"]))
    for row in (result["rows"][0], backward["rows"][0]):
        assert row["turn_angle_deg"] == pytest.approx(90)
        assert row["radius_jump_mm"] == 1
        assert row["position_gap_mm"] == 0
    assert result["acceptance_status"] == "UNKNOWN"
    assert case == before


def test_wrong_route_order_is_not_measured():
    with pytest.raises(ValueError, match="sequence"):
        measure_route_junctions(connected(), dict(edges=["b", "a"], nodes=["0", "1", "3"]))
