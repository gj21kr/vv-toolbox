import importlib
from pathlib import Path
import numpy as np
import pytest
import trimesh


def inspector(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    return importlib.import_module('inspect_atlas_edit_sections')


def test_sections_and_containment_of_known_cylinder(monkeypatch):
    module = inspector(monkeypatch)
    mesh = trimesh.creation.cylinder(radius=2., height=10., sections=128)
    edge = dict(points=[[0,0,-2],[0,0,0],[0,0,2]], radii=[2.,2.,2.])
    result = module.sections(mesh, edge)
    assert len(result) == 1 and result[0]['status'] == 'MEASURED'
    assert result[0]['metrics']['area_equivalent_radius_mm'] == pytest.approx(2., abs=.001)
    inside = module.containment(mesh, np.array([[0.,0,0],[3.,0,0]]))
    assert inside['inside_count'] == 1
    assert inside['outside_indices'] == [1]


def test_open_surface_containment_is_unknown(monkeypatch):
    module = inspector(monkeypatch)
    mesh = trimesh.Trimesh(vertices=[[0,0,0],[1,0,0],[0,1,0]], faces=[[0,1,2]], process=False)
    assert module.containment(mesh, np.array([[0.,0,0]]))['status'] == 'UNKNOWN'
