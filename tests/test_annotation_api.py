"""Draft API persistence contract; synthetic inputs only."""
import json
import pytest
from vv_toolbox.atlas_annotation_service import AnnotationStore, AnnotationConflict, require_renderable_frame


def store_and_payload(tmp_path):
    store = AnnotationStore(tmp_path/'drafts.json', 'a'*64)
    payload = dict(revision='new', boundary_id='B.L.ACA.A1_A2', reason='Attachment unresolved',
                   review_note='Needs inspection', source_refs=['source table'], candidate_position=[1, 2, 3])
    return store, payload


def test_draft_roundtrip_preserves_unresolved_boundary(tmp_path):
    store, payload = store_and_payload(tmp_path)
    result = store.update(payload)
    assert result == AnnotationStore(store.path, 'a'*64).read()
    boundary = result['document']['boundaries'][0]
    assert boundary['position'] is None
    assert boundary['evidence_status'] == 'unresolved'
    assert result['candidate_positions'][boundary['boundary_id']] == [1, 2, 3]
    assert result['document']['coordinate_frame']['units'] == 'mm'
    assert result['document']['coordinate_frame']['id'] == 'bodyparts3d_native_LPS'


def test_stale_revision_does_not_overwrite(tmp_path):
    store, payload = store_and_payload(tmp_path)
    saved = store.update(payload)
    with pytest.raises(AnnotationConflict):store.update(payload)
    assert store.read() == saved


@pytest.mark.parametrize('value', [[1, 2], [1, True, 3], [1, float('nan'), 3], [0, 0, 1000001]])
def test_invalid_candidate_leaves_no_file(tmp_path, value):
    store, payload = store_and_payload(tmp_path)
    payload['candidate_position'] = value
    with pytest.raises(ValueError):store.update(payload)
    assert not store.path.exists()


def test_candidate_can_be_cleared(tmp_path):
    store, payload = store_and_payload(tmp_path)
    result = store.update(payload)
    payload.update(revision=result['revision'], candidate_position=None)
    assert store.update(payload)['candidate_positions'] == {}


def test_source_mismatch_rejected(tmp_path):
    store, payload = store_and_payload(tmp_path)
    store.update(payload)
    with pytest.raises(ValueError):AnnotationStore(store.path, 'b'*64).read()


def test_cannot_submit_status_or_path(tmp_path):
    store, payload = store_and_payload(tmp_path)
    for key in ('evidence_status', 'path'):
        with pytest.raises(ValueError):store.update(dict(payload, **{key:'landmark_reviewed'}))


def test_corrupt_file_preserved(tmp_path):
    store, payload = store_and_payload(tmp_path)
    store.path.write_text('{broken', encoding='utf-8')
    with pytest.raises(ValueError):store.update(payload)
    assert store.path.read_text() == '{broken'


@pytest.mark.parametrize('value', [[], {}, {'document':{}}, {'document':{}, 'candidate_positions':{}, 'path':'ignored'}])
def test_malformed_envelope_rejected(tmp_path, value):
    store, _ = store_and_payload(tmp_path)
    store.path.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError):store.read()


@pytest.mark.parametrize('field,value', [('id','unknown'), ('units','cm'), ('units','unknown'), ('frame_confirmed',False), ('units_confirmed',False)])
def test_render_rejects_noncanonical_frame(tmp_path, field, value):
    store, _ = store_and_payload(tmp_path)
    document = store.read()['document']
    document['coordinate_frame'][field] = value
    with pytest.raises(ValueError, match='requires confirmed'):require_renderable_frame(document)


def test_render_accepts_native_mm_contract(tmp_path):
    store, _ = store_and_payload(tmp_path)
    require_renderable_frame(store.read()['document'])


def test_focus_rejects_unknown_frame_and_removes_old_point(tmp_path):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from vv_toolbox.app import Workspace
    store, payload = store_and_payload(tmp_path)
    value = store.update(payload)
    value['document']['coordinate_frame']['units']='cm'
    workspace=Workspace.__new__(Workspace)
    workspace.annotations=SimpleNamespace(read=lambda:value)
    old=Mock()
    workspace.annotation_point_handle=old
    workspace.server=Mock()
    with pytest.raises(ValueError, match='requires confirmed'):
        workspace.focus_annotation_candidate(payload['boundary_id'])
    old.remove.assert_called_once()
    assert workspace.annotation_point_handle is None
    workspace.server.scene.add_point_cloud.assert_not_called()


def test_clear_candidate_is_idempotent():
    from unittest.mock import Mock
    from vv_toolbox.app import Workspace
    workspace=Workspace.__new__(Workspace)
    old=Mock()
    workspace.annotation_point_handle=old
    workspace.clear_annotation_candidate()
    workspace.clear_annotation_candidate()
    old.remove.assert_called_once()
    assert workspace.annotation_point_handle is None
