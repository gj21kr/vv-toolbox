import importlib.util
from pathlib import Path
import numpy as np
import pytest

spec=importlib.util.spec_from_file_location('edit_surroundings_inspection',
    Path(__file__).resolve().parents[1]/'scripts/inspect_atlas_edit_surroundings.py')
inspection=importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspection)


def test_boundary_fold_detected_at_corresponding_face_pair():
    original=dict(vertices=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,-1,0]]),
                  faces=np.array([[0,1,2],[1,0,3]]))
    edited=dict(vertices=original['vertices'].copy(),faces=original['faces'])
    edited['vertices'][3]=[0,1,1]
    report=inspection.boundary_angles(original,edited)
    assert report['before']['max_deg']==pytest.approx(0)
    assert report['after']['max_deg']==pytest.approx(135)
    assert report['newly_above_90_pairs']==1
    assert report['smoothness']=='UNKNOWN'


def test_unchanged_mesh_has_no_moving_boundary():
    original=dict(vertices=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,-1,0]]),
                  faces=np.array([[0,1,2],[1,0,3]]))
    report=inspection.boundary_angles(original,original)
    assert report['after']['count']==0
    assert report['after']['max_deg'] is None
