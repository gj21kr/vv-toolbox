import hashlib
import json

import numpy as np
import pytest

from test_interval_application import prepared
from test_atlas_interval_preview import fixture
from vv_toolbox.atlas_interval_preview import preview_interval
from vv_toolbox.case_io import _encode
from vv_toolbox.interval_application import apply_interval, undo_interval
from vv_toolbox.interval_snapshot import encode_interval_snapshot
from vv_toolbox.interval_session import encode_session, restore_session


def two_edits():
    ws, text, _ = prepared()
    apply_interval(ws, text, ws.generation, lambda: None)
    _, request = fixture()
    text = encode_interval_snapshot(preview_interval(ws, request))[0].decode()
    apply_interval(ws, text, ws.generation, lambda: None)
    return ws


def test_saved_two_edits_restore_exactly_and_can_undo():
    ws = two_edits()
    text, revision = encode_session(ws)
    target, _, _ = prepared()
    calls = []
    result = restore_session(target, text.decode(), target.generation, lambda: calls.append(target.generation))
    assert result['revision'] == revision and result['operations'] == 2
    assert calls == [8]
    assert np.array_equal(target.atlas_modified_parts['vessel']['vertices'], ws.atlas_modified_parts['vessel']['vertices'])
    undo_interval(target, 8, lambda: None)
    assert len(target.atlas_interval_edits['vessel']) == 1
    undo_interval(target, 9, lambda: None)
    assert target.atlas_modified_parts == {} and target.atlas_interval_edits == {}


def test_later_failure_never_publishes_earlier_success():
    ws = two_edits()
    data = json.loads(encode_session(ws)[0])
    # Valid envelopes, but impossible second target tolerance: must rerun checks.
    second = json.loads(data['content']['snapshots'][1])['candidate']
    second['interval_edit']['absolute_scale_tolerance'] = 0.
    data['content']['snapshots'][1] = encode_interval_snapshot(second)[0].decode()
    data['revision'] = hashlib.sha256(_encode(data['content'])).hexdigest()
    target, _, _ = prepared()
    with pytest.raises(ValueError, match='section target check FAIL'):
        restore_session(target, json.dumps(data), 7, lambda: pytest.fail('must not render'))
    assert target.atlas_modified_parts == {} and target.generation == 7
    assert target.interval_preview_busy is False


def test_corrupt_session_rejected_without_state_change():
    ws = two_edits()
    data = json.loads(encode_session(ws)[0])
    data['content']['snapshots'].reverse()
    target, _, _ = prepared()
    with pytest.raises(ValueError, match='hash mismatch'):
        restore_session(target, json.dumps(data), 7, lambda: pytest.fail('must not render'))
    assert target.atlas_modified_parts == {}


def test_rehashed_wrong_order_still_fails_reference_check():
    ws = two_edits()
    data = json.loads(encode_session(ws)[0])
    data['content']['snapshots'].reverse()
    data['revision'] = hashlib.sha256(_encode(data['content'])).hexdigest()
    target, _, _ = prepared()
    with pytest.raises(ValueError, match='current scene'):
        restore_session(target, json.dumps(data), 7, lambda: pytest.fail('must not render'))
    assert target.atlas_modified_parts == {} and target.generation == 7


def test_new_edit_after_restore_keeps_unique_operation_order():
    ws = two_edits()
    target, _, _ = prepared()
    restore_session(target, encode_session(ws)[0].decode(), 7, lambda: None)
    _, request = fixture()
    request['factor'] = 1.
    text = encode_interval_snapshot(preview_interval(target, request))[0].decode()
    apply_interval(target, text, target.generation, lambda: None)
    data = json.loads(encode_session(target)[0])
    assert [json.loads(s)['candidate']['operation_index'] for s in data['content']['snapshots']] == [1, 2, 3]
