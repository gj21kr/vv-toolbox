import numpy as np
import pytest

from vv_toolbox.path_link_candidates import enumerate_path_links


def test_every_branch_pair_retained_without_modifying_paths():
    first = {"short": np.array([[0., 0, 0], [1, 0, 0]]),
             "long": np.array([[0., 5, 0], [20, 5, 0]])}
    second = {"other": np.array([[1., 1, 0], [2, 1, 0]])}
    before = {k: v.copy() for k, v in first.items()}
    rows = enumerate_path_links(first, second)
    assert {r["first_edge"] for r in rows} == {"short", "long"}
    short = next(r for r in rows if r["first_edge"] == "short")
    assert short["distance_mm"] == 1
    assert short["connection_status"] == "UNADJUDICATED"
    assert all(np.array_equal(first[k], v) for k, v in before.items())


def test_ties_resolve_to_first_sample_and_zero_gap_is_not_approval():
    rows = enumerate_path_links({"a": [[0, 0, 0], [1, 0, 0]]},
                                {"b": [[0, 0, 0], [0, 0, 0]]})
    assert (rows[0]["first_index"], rows[0]["second_index"]) == (0, 0)
    assert rows[0]["distance_mm"] == 0
    assert rows[0]["connection_status"] == "UNADJUDICATED"


@pytest.mark.parametrize("invalid", [{}, {"x": [[0, 0, 0]]},
                                      {"x": [[0, 0, 0], [float("nan"), 1, 0]]}])
def test_invalid_maps_rejected(invalid):
    with pytest.raises(ValueError):
        enumerate_path_links(invalid, {"b": [[0, 0, 0], [1, 0, 0]]})
