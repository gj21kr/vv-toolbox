import importlib
from pathlib import Path
import numpy as np
import pytest


@pytest.fixture
def centroid(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    return importlib.import_module('recenter_testicular_candidate').area_centroid


def test_rectangle_area_centroid_and_reversed_winding(centroid):
    points=np.array([[10,20,0],[14,20,0],[14,22,0],[10,22,0],[10,20,0]])
    assert centroid(points)==pytest.approx([12,21])
    assert centroid(points[::-1])==pytest.approx([12,21])


def test_centroid_independent_of_vertex_density(centroid):
    points=[[0,0],[1,0],[2,0],[3,0],[4,0],[4,2],[0,2],[0,0]]
    assert centroid(points)==pytest.approx([2,1])


@pytest.mark.parametrize('points', [[[0,0],[1,0],[1,1],[0,1]],[[0,0],[1,0],[2,0],[0,0]]])
def test_invalid_section_rejected(centroid,points):
    with pytest.raises(ValueError):centroid(points)
