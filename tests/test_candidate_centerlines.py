import numpy as np
import pytest

from vv_toolbox.candidate_centerlines import bind_source_centerlines


def fixture():
    return dict(surface_parts=[dict(part_id='artery', edge_ids=['edge'])],
                edges=[dict(id='edge', centerline_mm=[[0, 0, 0], [0, 0, 2]])])


def test_bound_path_is_independent_and_revision_locked():
    case = fixture()
    paths, unavailable = bind_source_centerlines(case, 'rev', 'rev', ['artery'])
    assert not unavailable
    assert paths['artery']['edge_id'] == 'edge'
    paths['artery']['points_mm'][0, 0] = 9
    assert case['edges'][0]['centerline_mm'][0][0] == 0
    with pytest.raises(ValueError, match='revision'):
        bind_source_centerlines(case, 'new', 'old', ['artery'])


def test_branch_ambiguity_never_silently_selects_path():
    case = fixture()
    case['surface_parts'][0]['edge_ids'].append('other')
    paths, unavailable = bind_source_centerlines(case, 'rev', 'rev', ['artery'])
    assert not paths and 'artery' in unavailable


def test_declared_connector_path_preserved():
    case = fixture()
    points = [[1, 0, 0], [1, 0, 2]]
    case['inspection'] = dict(atlas_scene_capture=dict(
        estimated_metadata=dict(artery=dict(centerline=points))))
    paths, _ = bind_source_centerlines(case, 'rev', 'rev', ['artery'])
    assert np.array_equal(paths['artery']['points_mm'], points)
    assert paths['artery']['provenance'] == 'declared-estimate'


def test_invalid_path_unavailable():
    case = fixture()
    case['edges'][0]['centerline_mm'] = [[0, 0, 0], [0, 0, 0]]
    paths, unavailable = bind_source_centerlines(case, 'rev', 'rev', ['artery'])
    assert not paths and 'artery' in unavailable
