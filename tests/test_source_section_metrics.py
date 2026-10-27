import importlib
from pathlib import Path
import numpy as np
import pytest


def test_area_centroid_and_nearest_boundary(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    metrics=importlib.import_module('inspect_iliac_normal_sections').section_metrics
    # An offset rectangle exercises segment-interior nearest points.
    p=np.array([[1.,2.],[5.,2.],[5.,4.],[1.,4.],[1.,2.]])
    for contour in (p,p[::-1]):
        result=metrics(contour)
        assert result['area_mm2']==pytest.approx(8)
        assert result['area_equivalent_radius_mm']==pytest.approx(np.sqrt(8/np.pi))
        assert result['centroid_uv_mm']==pytest.approx([3,3])
        assert result['minimum_centroid_boundary_distance_mm']==pytest.approx(1)
        assert result['maximum_centroid_vertex_distance_mm']==pytest.approx(np.sqrt(5))
