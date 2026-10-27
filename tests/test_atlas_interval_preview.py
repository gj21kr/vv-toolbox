from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest
import trimesh

from vv_toolbox.atlas_interval_preview import preview_interval, snapshot_interval_workspace
from vv_toolbox.atlas_edit_checks import AtlasEditCheckFailure


def fixture():
    mesh = trimesh.creation.revolve([[0, -5], *[[1, z] for z in range(-5, 6)], [0, 5]], sections=16)
    part = dict(id='vessel', layer='arterial', vertices=mesh.vertices.copy(), faces=mesh.faces.copy())
    ws = SimpleNamespace(source='atlas', atlas=SimpleNamespace(meshes=[part]), neck_parts=[],
                         atlas_modified_parts={}, generation=7,
                         atlas_centerlines=dict(edges=[dict(id='edge', part_id='vessel',
                                                           points=[[0, 0, z] for z in range(-4, 5)])]))
    raw = dict(part_id='vessel', edge_id='edge', start_mm=1., end_mm=5., factor=.9,
               max_displacement_mm=.3, absolute_scale_tolerance=.09)
    return ws, raw


def test_preview_returns_geometry_without_changing_active_scene():
    ws, raw = fixture()
    original = ws.atlas.meshes[0]['vertices'].copy()
    result = preview_interval(ws, raw)
    assert result['read_only'] and not result['applied']
    assert result['generation'] == 7 and result['checks']['section_targets']['status'] == 'PASS'
    assert np.array_equal(original, ws.atlas.meshes[0]['vertices'])
    assert not ws.atlas_modified_parts and ws.generation == 7


def test_actual_current_neighbor_is_checked():
    ws, raw = fixture()
    neighbor = deepcopy(ws.atlas.meshes[0])
    neighbor['id'] = 'neighbor'
    neighbor['vertices'] += [10, 0, 0]
    ws.atlas.meshes.append(neighbor)
    result = preview_interval(ws, raw)
    assert result['checks']['neighbor_surface_contacts']['expected_ids'] == ['neighbor']


def test_failure_never_changes_active_state():
    ws, raw = fixture()
    raw['absolute_scale_tolerance'] = 0.
    before = ws.atlas.meshes[0]['vertices'].copy()
    with pytest.raises(AtlasEditCheckFailure):
        preview_interval(ws, raw)
    assert np.array_equal(before, ws.atlas.meshes[0]['vertices'])
    assert ws.generation == 7 and not ws.atlas_modified_parts


def test_multibranch_part_is_not_silently_deformed():
    ws, raw = fixture()
    ws.atlas_centerlines['edges'].append(dict(id='branch', part_id='vessel', points=[]))
    with pytest.raises(ValueError, match='multi-branch'):
        preview_interval(ws, raw)


def test_scene_snapshot_does_not_follow_concurrent_changes():
    ws, raw = fixture()
    snapshot = snapshot_interval_workspace(ws, raw)
    original = snapshot.atlas.meshes[0]['vertices'].copy()
    ws.atlas.meshes[0]['vertices'] += 100
    ws.atlas_centerlines['edges'][0]['points'][0][0] += 100
    ws.generation += 1
    assert np.array_equal(snapshot.atlas.meshes[0]['vertices'], original)
    assert snapshot.atlas_centerlines['edges'][0]['points'][0][0] == 0
    assert snapshot.generation == 7
