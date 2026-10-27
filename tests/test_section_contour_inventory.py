import numpy as np
import pytest
import trimesh

from vv_toolbox.source_sections import extract_source_sections


def test_disconnected_contour_is_retained_without_branch_identity_claim():
    first = trimesh.creation.box(extents=[2, 2, 4])
    second = first.copy()
    second.apply_translation([5, 0, 0])
    surface = trimesh.util.concatenate([first, second])
    points = [[0, 0, -1], [0, 0, 0], [0, 0, 1]]
    result = extract_source_sections(surface, points, include_all_contours=True)
    row = result["profiles"][0]
    assert row["status"] == "MEASURED"
    assert len(row["all_contours"]) == 2
    assert sorted(p["contains_origin"] for p in row["all_contours"]) == [False, True]
    assert all(p["anatomical_branch_identity"] == "UNKNOWN" for p in row["all_contours"])
    assert all(np.isclose(p["area_mm2"], 4) for p in row["all_contours"])
    baseline = extract_source_sections(surface, points)["profiles"][0]
    assert "all_contours" not in baseline
    assert baseline["contour_xyz_mm"] == row["contour_xyz_mm"]


def test_invalid_inventory_option_rejected():
    with pytest.raises(ValueError):
        extract_source_sections(trimesh.creation.box(), [[0, 0, -1], [0, 0, 0], [0, 0, 1]],
                                include_all_contours="yes")
