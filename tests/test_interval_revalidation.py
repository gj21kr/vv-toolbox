from copy import deepcopy

import numpy as np
import pytest

from test_atlas_interval_preview import fixture
from vv_toolbox.atlas_interval_preview import preview_interval
from vv_toolbox.interval_snapshot import encode_interval_snapshot
from vv_toolbox.interval_revalidation import revalidate_interval_snapshot


@pytest.fixture(scope='module')
def saved():
    workspace, request = fixture()
    workspace.atlas.metadata = dict(sha256='a' * 64)
    candidate = preview_interval(workspace, request)
    return workspace, candidate, encode_interval_snapshot(candidate)[0].decode()


def test_regeneration_matches_saved_geometry_and_preserves_current_state(saved):
    workspace, candidate, text = saved
    before = workspace.atlas.meshes[0]['vertices'].copy()
    result = revalidate_interval_snapshot(workspace, text)
    assert result['revalidation']['status'] == 'PASS'
    assert result['vertices'] == candidate['vertices']
    assert result['applied'] is False and workspace.generation == 7
    assert np.array_equal(before, workspace.atlas.meshes[0]['vertices'])


def test_changed_current_geometry_rejected_before_regeneration(saved):
    workspace, _, text = saved
    changed = deepcopy(workspace)
    changed.atlas.meshes[0]['vertices'][0, 0] += .1
    with pytest.raises(ValueError, match='current scene'):
        revalidate_interval_snapshot(changed, text)


def test_changed_centerline_rejected(saved):
    workspace, _, text = saved
    changed = deepcopy(workspace)
    changed.atlas_centerlines['edges'][0]['points'][1][0] += .01
    with pytest.raises(ValueError, match='current scene'):
        revalidate_interval_snapshot(changed, text)


def test_recorded_pass_is_not_used_instead_of_running_checks(saved):
    workspace, candidate, _ = saved
    changed = deepcopy(candidate)
    changed['interval_edit']['absolute_scale_tolerance'] = 0.
    text, _ = encode_interval_snapshot(changed)
    with pytest.raises(ValueError, match='section target check FAIL'):
        revalidate_interval_snapshot(workspace, text.decode())


def test_revalidation_checks_neighbors_added_since_file_was_saved(saved):
    workspace, _, text = saved
    changed = deepcopy(workspace)
    neighbor = deepcopy(changed.atlas.meshes[0])
    neighbor['id'] = 'new-neighbor'
    neighbor['vertices'] += [10, 0, 0]
    changed.atlas.meshes.append(neighbor)
    result = revalidate_interval_snapshot(changed, text)
    assert result['checks']['neighbor_surface_contacts']['expected_ids'] == ['new-neighbor']
    assert result['revalidation']['status'] == 'PASS'
